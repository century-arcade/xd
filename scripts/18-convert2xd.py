#!/usr/bin/env python3

# Usage: $0 [-o <output-xd.zip>] <input>
#
#   Converts file in <input> to .xd, maintaining the original directory structure.
#   Appends to receipts.tsv
#

from collections import namedtuple

import time
import zipfile

from xdfile import IncompletePuzzleParse

from xdfile.utils import log, debug, log_error
from xdfile.utils import find_files_with_time, parse_pathname, replace_ext, strip_toplevel
from xdfile.utils import args_parser, get_args, parse_tsv_data, iso8601, open_output, progress

from xdfile import metadatabase as metadb

from xdfile.ccxml2xd import parse_ccxml
from xdfile.uxml2xd import parse_uxml
from xdfile.ujson2xd import parse_ujson
from xdfile.puz2xd import parse_puz
from xdfile.xwordinfo2xd import parse_xwordinfo

from xdfile import catalog

import xdfile

def main():
    global args
    parsers = {
        '.xml': [parse_ccxml, parse_uxml],
        '.json': [parse_ujson],
        '.puz': [parse_puz],
        '.html': [parse_xwordinfo],
        '.pdf': [],
        '.jpg': [],
        '.gif': [],
        '.xd': [],  # special case, just copy the input, in case re-emitting screws it up
    }

    p = args_parser('convert crosswords to .xd format')
    p.add_argument('--copyright', default=None, help='Default value for unspecified Copyright headers')
    p.add_argument('--source', default=None, help='Value for receipts.ExternalSource')
    p.add_argument('--pubid', default=None, help='PublicationAbbr (pubid) to use')
    args = get_args(parser=p)

    outf = open_output()

    nextReceiptId = metadb.get_last_receipt_id() + 1

    for input_source in args.inputs:
      try:
        # collect 'sources' metadata
        source_files = {}
        for fn, contents, dt in find_files_with_time(input_source, ext='.tsv'):
            progress(fn)
#            assert fn.endswith('sources.tsv'), fn
            for row in parse_tsv_data(contents.decode('utf-8'), "Source"):
                innerfn = strip_toplevel(row.SourceFilename)
                if innerfn in source_files:
                    log("%s: already in source_files!" % innerfn)
                    continue
                source_files[innerfn] = row

        # enumerate all files in this source, reverse-sorted by time
        #  (so most recent edition gets main slot in case of shelving
        #  conflict)
        for fn, contents, dt in sorted(find_files_with_time(input_source, strip_toplevel=False), reverse=True, key=lambda x: x[2]):
            if fn.endswith(".tsv") or fn.endswith(".log"):
                continue

            if not contents:  # 0-length files
                continue

            innerfn = strip_toplevel(fn)
            if innerfn in source_files:
                srcrow = source_files[innerfn]
                CaptureTime = srcrow.DownloadTime
                ExternalSource = args.source or srcrow.ExternalSource
                SourceFilename = innerfn
            else:
                debug("%s not in sources.tsv" % innerfn)
                CaptureTime = iso8601(dt)
                ExternalSource = args.source or parse_pathname(input_source).filename
                SourceFilename = innerfn

            ReceiptId = nextReceiptId
            nextReceiptId += 1

            ReceivedTime = iso8601(time.time())
            InternalSource = parse_pathname(input_source).filename

            already_received = list(r for r in metadb.xd_receipts().values()
                           if r.ExternalSource == ExternalSource
                           and r.SourceFilename == SourceFilename)

            xdid = ""
            prev_xdid = ""  # unshelved by default

            existing_xdids = set(r.xdid for r in already_received)

            if existing_xdids:

                if len(existing_xdids) > 1:
                    log('previously received this same file under multiple xdids:' + ' '.join(existing_xdids))
                else:
                    prev_xdid = existing_xdids.pop()
                    debug('already received as %s' % prev_xdid)

            # try each parser by extension
            ext = parse_pathname(fn).ext.lower()
            possible_parsers = parsers.get(ext, parsers[".puz"])

            if ext == ".xd":
                outf.write_file(fn, contents.decode('utf-8'), dt)
            elif not possible_parsers:
                rejected = "no parser"
            else:
                rejected = ""
                for parsefunc in possible_parsers:
                    try:
                        try:
                            xd = parsefunc(contents, fn)
                        except IncompletePuzzleParse as e:
                            log_error("%s  %s" % (fn, e))
                            xd = e.xd
                        
                        if not xd:
                            continue

                        xd.filename = replace_ext(strip_toplevel(fn), ".xd")
                        if not xd.get_header("Copyright"):
                            if args.copyright:
                                xd.set_header("Copyright", args.copyright)

                        catalog.deduce_set_seqnum(xd)

                        xdstr = xd.to_unicode()

                        mdtext = "|".join((ExternalSource,InternalSource,SourceFilename))
                        xdid = prev_xdid or catalog.deduce_xdid(xd, mdtext)
                        path = catalog.get_shelf_path(xd, args.pubid, mdtext)
                        outf.write_file(path + ".xd", xdstr, dt)
                        #progress("converted by %s (%s bytes)" % (parsefunc.__name__, len(xdstr)))
                        
                        rejected = ""
                        break  # stop after first successful parsing
                    except xdfile.NoShelfError as e:
                        log_error("could not shelve: %s" % str(e))
                        rejected += "[shelver] %s  " % str(e)
                    except Exception as e:
                        log_error("%s could not convert [%s]: %s" % (parsefunc.__name__, fn, str(e)))
                        rejected += "[%s] %s  " % (parsefunc.__name__, str(e))
                        #if args.debug:
                        #    raise

                if rejected:
                    log_error("could not convert: %s" % rejected)

                # only add receipt if first time converting this source
                if xdid and not already_received:
                    this_receipt = metadb.xd_receipts_row(ReceiptId=ReceiptId,
                        CaptureTime=CaptureTime,
                        ReceivedTime=ReceivedTime,
                        ExternalSource=ExternalSource,
                        InternalSource=InternalSource,
                        SourceFilename=SourceFilename,
                        xdid=xdid)

                    metadb.append_receipts(this_receipt)

      except Exception as e:
          log(str(e))
          if args.debug:
              raise


if __name__ == "__main__":
    main()
