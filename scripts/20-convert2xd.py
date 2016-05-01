#!/usr/bin/env python

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
from xdfile.utils import find_files, parse_pathname, replace_ext, filetime, strip_toplevel
from xdfile.utils import get_args, parse_tsv, iso8601, open_output

from xdfile.metadatabase import xd_receipts_header, xd_receipts_row, append_receipts, get_last_receipt_id

from xdfile.ccxml2xd import parse_ccxml
from xdfile.uxml2xd import parse_uxml
from xdfile.ujson2xd import parse_ujson
from xdfile.puz2xd import parse_puz
from xdfile.xwordinfo2xd import parse_xwordinfo


def main():
    parsers = {
        '.xml': [parse_ccxml, parse_uxml],
        '.json': [parse_ujson],
        '.puz': [parse_puz],
        '.html': [parse_xwordinfo],
        '.pdf': [],
        '.jpg': [],
        '.gif': []
    }

    args = get_args(desc='convert crosswords to .xd format')

    outf = open_output()

    new_receipts = xd_receipts_header

    nextReceiptId = get_last_receipt_id() + 1

    for input_source in args.inputs:
        # collect 'sources' metadata
        source_files = {}
        for fn, contents in find_files(input_source, ext='.tsv'):
            assert fn.endswith('sources.tsv'), fn
            for row in parse_tsv(contents, "Source"):
                if row.SourceFilename in source_files:
                    log("%s: already in source_files!" % row.SourceFilename)
                    continue
                source_files[row.SourceFilename] = row

        # enumerate all files in this source
        for fn, contents in find_files(input_source, strip_toplevel=False):
            if fn.endswith(".tsv") or fn.endswith(".log"):
                continue

            sources_row = namedtuple("Source", "ReceiptId DownloadTime ReceivedTime ExternalSource InternalSource SourceFilename Rejected")
            if fn in source_files:
                srcrow = source_files[fn]
                sources_row.DownloadTime = srcrow.DownloadTime
                sources_row.ExternalSource = srcrow.ExternalSource
                sources_row.SourceFilename = srcrow.SourceFilename
            else:
                log("%s not in sources.tsv, [0]=%s" % (fn, source_files.keys()[0]))
                sources_row.DownloadTime = iso8601(filetime(fn))
                sources_row.ExternalSource = input_source
                sources_row.SourceFilename = fn

            sources_row.ReceiptId = nextReceiptId
            nextReceiptId += 1

            sources_row.ReceivedTime = iso8601(time.time())
            sources_row.InternalSource = input_source

            # try each parser by extension
            possible_parsers = parsers.get(parse_pathname(fn).ext.lower(), parsers[".puz"])

            if not possible_parsers:
                sources_row.Rejected = "no parser"
            else:
                sources_row.Rejected = ""
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

                        xdstr = xd.to_unicode()
                        outf.write_file(xd.filename, xdstr.encode("utf-8"))
                        debug("converted by %s (%s bytes)" % (parsefunc.__name__, len(xdstr)))
                        sources_row.Rejected = ""
                        break  # stop after first successful parsing
                    except Exception, e:
                        debug("%s could not convert: %s" % (parsefunc.__name__, str(e)))
                        sources_row.Rejected += "[%s] %s  " % (parsefunc.__name__, str(e))
                        if args.debug:
                            raise

                if sources_row.Rejected:
                    log("could not convert: %s" % sources_row.Rejected)

            this_receipt = xd_receipts_row(sources_row)
            new_receipts += this_receipt

    outf.write_file("receipts.tsv", new_receipts.encode("utf-8"))
    outf.write_file("converted.log", get_log().encode("utf-8"))

    # only append to global receipts.tsv if entire conversion process succeeded
    append_receipts(new_receipts)


if __name__ == "__main__":
    main()
