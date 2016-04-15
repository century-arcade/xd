#!/usr/bin/env python

# Usage:
#   $0 -o <output-zip> <toplevel-directory>
#
#    zips all files under <toplevel-directory>. includes .log of process and .tsv of contents

from __future__ import print_function

import sys
import zipfile

from xdfile.metadatabase import xd_source_row, xd_source_header
from xdfile.utils import find_files, zip_append, get_log, get_args, filetime, args_parser, parse_pathname, log, iso8601


def main():
    p = args_parser('catalog source files and create source.tsv')
    p.add_argument('-s', '--source', default=None, help='ExternalSource')
    args = get_args(p)

    log("importing from %s" % args.source)

    zf = zipfile.ZipFile(args.output, 'w')

    sources = xd_source_header

    for input_source in args.inputs:
        for fn, contents in find_files(input_source):
            if len(contents) == 0:
                log("ignoring empty file")
                continue

            dt = filetime(fn)

            zip_append(zf, fn, contents, dt)

            sources += xd_source_row(fn, args.source or input_source, iso8601(dt))

    log("Done")

    outbase = parse_pathname(args.output).base

    zip_append(zf, "%s.tsv" % outbase, sources)
    zip_append(zf, "%s.log" % outbase, get_log())

main()
