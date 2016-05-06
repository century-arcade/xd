#!/usr/bin/env python3

# Usage:
#   $0 -o <output-zip> <toplevel-directory>
#
#    zips all files under <toplevel-directory>. includes .log of process and .tsv of contents

import zipfile

from xdfile.metadatabase import xd_sources_row, xd_sources_header
from xdfile.utils import find_files, get_log, get_args, filetime, args_parser, parse_pathname, log, iso8601, open_output, strip_toplevel


def main():
    p = args_parser('catalog source files and create source.tsv')
    p.add_argument('-s', '--source', default=None, help='ExternalSource')
    args = get_args(parser=p)

    log("importing from %s" % args.source)

    outf = open_output()

    sources = []

    for input_source in args.inputs:
        for fn, contents in find_files(input_source):
            if len(contents) == 0:
                log("ignoring empty file")
                continue

            outf.write_file(strip_toplevel(fn), contents, filetime(fn))

            sources.append(xd_sources_row(fn, args.source or input_source, iso8601(dt)))

    log("%s files cataloged" % len(sources))

    outbase = parse_pathname(args.output).base

    outf.write_file("%s.tsv" % outbase, xd_sources_header + "".join(sources))
    outf.write_file("%s.log" % outbase, get_log())

main()
