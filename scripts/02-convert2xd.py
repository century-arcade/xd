#!/usr/bin/env python

# Usage: $0 [-o <output-xd.zip>] <input>
#
#   Converts file in <input> to .xd, maintaining the original directory structure.
#   Appends to receipts.tsv
#

import os.path
import sys
import zipfile

from ccxml2xd import parse_ccxml
from uxml2xd import parse_uxml
from ujson2xd import parse_ujson
from puz2xd import parse_puz
from xwordinfo2xd import parse_xwordinfo

def main():
    parsers = { 
        '.xml': [ parse_ccxml, parse_uxml ],
        '.json': [ parse_ujson ],
        '.puz': [ parse_puz ],
        '.html': [ parse_xwordinfo ]
        '.pdf': [ ]
    }

    xdzf = zipfile.ZipFile(args.output, 'w')

    new_receipts = xd_receipts_header()

    nextReceiptId = xd_receipts_meta()[-1].ReceiptId + 1

    args = util.get_args('convert crosswords to .xd format')
    for input_source in args.inputs:
        # collect 'sources' metadata
        source_files = {}
        for fn, contents in utils.find_files(*args.inputs, ext='tsv'):
            for row in parse_tsv(contents):
                if row.SourceFilename in source_files:
                    log("%s: already in source_files!" % row.SourceFilename)
                    continue
                source_files[row.SourceFilename] = row

        # enumerate all files in this source
        for fn, contents in utils.find_files(*args.inputs):
            util.progress(fn)

            if fn in source_files:
                sources_row = source_files[fn]
            else:
                sources_row = {
                    .DownloadTime = filetime(fn),
                    .ExternalSource = input_source,
                    .SourceFilename = fn
                }

            sources_row.ReceiptId = nextReceiptId
            nextReceiptId += 1

            sources_row.ReceivedTime = time.time()
            sources_row.InternalSource = args.output
                    
            # try each parser by extension
            for parsefunc in parsers.get(parse_filename(fn).ext.lower(), []):
                try:
                    try:
                        xd = parserfunc(contents, fullfn)
                    except IncompletePuzzleParse as e:
                        log("%s  %s" % (fullfn, e))
                        xd = e.xd

                    if not xd:
                        continue

                    xdstr = xd.to_unicode().encode("utf-8")
                    zip_append(xdzf, replace_ext(fn, ".xd"), xdstr)
                    log("%s converted by %s (%s bytes)" % (fn, parsefunc.__name__, len(xdstr)))

                    break
                except Exception, e:
                    log("%s not converted: %s" % (parsefunc.__name__, str(e)))
                    sources_row.Rejected = str(e)

            new_receipts += xd_receipts_row(sources_row)

       append_receipts(new_receipts)
       zip_append(xdzf, base + "-receipts.tsv", new_receipts)
       zip_append(xdzf, base + "converted.log", get_log())


if __name__ == "__main__":
    main()
