#!/usr/bin/env python

# Usage: $0 [-o <puzzles.tsv>] <input>
#
#   Appends rows to puzzles.tsv for each .xd in <input>.  
#

from collections import namedtuple

import os.path
import sys
import time
import zipfile

from xdfile import corpus

from xdfile.utils import log, debug, get_log
from xdfile.utils import find_files, parse_pathname, replace_ext, filetime
from xdfile.utils import get_args, parse_tsv, iso8601, zip_append

from xdfile.metadatabase import xd_puzzles_header, xd_puzzles_row

def main():
    args = get_args(desc='appends rows to puzzles.tsv')

    if args.output:
        outfp = file(args.output, 'w')
    else:
        outfp = sys.stdout

    outfp.write(xd_puzzles_header)

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents, fn)
            outfp.write(xd_puzzles_row(xd))


if __name__ == "__main__":
    main()
