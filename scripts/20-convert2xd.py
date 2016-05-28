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

from xdfile.utils import log, debug, get_log
from xdfile.utils import find_files_with_time, parse_pathname, replace_ext, strip_toplevel
from xdfile.utils import args_parser, get_args, parse_tsv_data, iso8601, open_output

from xdfile.metadatabase import xd_receipts_header, xd_receipts_row, append_receipts, get_last_receipt_id

from xdfile.ccxml2xd import parse_ccxml
from xdfile.uxml2xd import parse_uxml
from xdfile.ujson2xd import parse_ujson
from xdfile.puz2xd import parse_puz
from xdfile.xwordinfo2xd import parse_xwordinfo

import xdfile

def main():
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
    args = get_args(parser=p)

    outf = open_output()

    new_receipts = ''

    nextReceiptId = get_last_receipt_id() + 1

    for input_source in args.inputs:
      try:
        # collect 'sources' metadata
        source_files = {}
        for fn, contents, dt in find_files_with_time(input_source, ext='.tsv'):
#            assert fn.endswith('sources.tsv'), fn
            for row in parse_tsv_data(contents.decode('utf-8'), "Source"):
                innerfn = strip_toplevel(row.SourceFilename)
                if innerfn in source_files:
                    log("%s: already in source_files!" % innerfn)
                    continue
                source_files[innerfn] = row

        # enumerate all files in this source
        for fn, contents, dt in find_files_with_time(input_source, strip_toplevel=False):
            if fn.endswith(".tsv") or fn.endswith(".log"):
                continue

            innerfn = strip_toplevel(fn)
            if innerfn in source_files:
                srcrow = source_files[innerfn]
                DownloadTime = srcrow.DownloadTime
                ExternalSource = srcrow.ExternalSource
                SourceFilename = innerfn
            else:
                log("%s not in sources.tsv" % innerfn)
                DownloadTime = iso8601(dt)
                ExternalSource = parse_pathname(input_source).filename
                SourceFilename = innerfn

            ReceiptId = nextReceiptId
            nextReceiptId += 1

            ReceivedTime = iso8601(time.time())
            InternalSource = parse_pathname(input_source).filename

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
                            log("%s  %s" % (fn, e))
                            xd = e.xd

                        if not xd:
                            continue

                        xd.filename = replace_ext(strip_toplevel(fn), ".xd")
                        if not xd.get_header("Copyright"):
                            if args.copyright:
                                xd.set_header("Copyright", args.copyright)

                        xdstr = xd.to_unicode()
                        outf.write_file(xd.filename, xdstr, dt)
                        debug("converted by %s (%s bytes)" % (parsefunc.__name__, len(xdstr)))
                        rejected = ""
                        break  # stop after first successful parsing
                    except Exception as e:
                        debug("%s could not convert: %s" % (parsefunc.__name__, str(e)))
                        rejected += "[%s] %s  " % (parsefunc.__name__, str(e))
                        if args.debug:
                            raise

                if rejected:
                    log("could not convert: %s" % rejected)

            this_receipt = xd_receipts_row(ReceiptId=ReceiptId,
                    DownloadTime=DownloadTime,
                    ReceivedTime=ReceivedTime,
                    ExternalSource=ExternalSource,
                    InternalSource=InternalSource,
                    SourceFilename=SourceFilename,
                    PubYear="")

            append_receipts(this_receipt)

            new_receipts += this_receipt
      except Exception as e:
          log(str(e))
          if args.debug:
              raise

    outf.write_file("receipts.tsv", xd_receipts_header + new_receipts)


if __name__ == "__main__":
    main()
