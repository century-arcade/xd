#!/usr/bin/env python3

""" Splits complex puzzle repos (like BWH) into separate zips """
import os
import sys
import re
from xdfile.utils import progress, iso8601, get_args, args_parser, open_output, parse_pathname
from xdfile.utils import filetime
import xdfile.utils
from xdfile.metadatabase import xd_sources_row, xd_sources_header


p = args_parser('process huge puzzles archive into separate .zip and create sources.tsv')
p.add_argument('-s', '--source', default=None, help='ExternalSource')
args = get_args(parser=p)

outf = open_output()

if args.source:
    source = args.source
else:
    source = parse_pathname(args.inputs[0]).base

subzips = {}

for inputfn in args.inputs:
    for fn, contents, dt in xdfile.utils.find_files_with_time(inputfn):
        if not contents:
            continue

        m = re.match(r'^([a-z]{2,4})[\-0-9]{1}\d.*', parse_pathname(fn).base, flags=re.IGNORECASE)
        prefix = m.group(1).lower() if m else 'misc'
        
        if prefix not in subzips:
            zf = xdfile.utils.OutputZipFile(os.path.join(args.output, prefix + ".zip"))
            sources = []
            subzips[prefix] = (zf, sources)
        else:
            zf, sources = subzips[prefix]
        
        progress("Processing %s -> %s" % (fn, prefix))
       
        zf.write_file(fn, contents, dt)

        sources.append(xd_sources_row(fn, source, iso8601(dt)))

for zf, sources in subzips.values():
    zf.write_file("sources.tsv", xd_sources_header + "".join(sources))

