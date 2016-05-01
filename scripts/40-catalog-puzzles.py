#!/usr/bin/env python

# Usage: $0 [-o <puzzles.tsv>] <input>
#
#   Appends rows to puzzles.tsv for each .xd in <input>.  
#

from xdfile.utils import find_files, get_args, open_output
from xdfile.metadatabase import xd_puzzles_header, xd_puzzles_row
from xdfile import corpus, xdfile

def main():
    args = get_args(desc='appends rows to puzzles.tsv')

    outf = open_output()

    outf.write(xd_puzzles_header)

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents, fn)
            outf.write(xd_puzzles_row(xd))


if __name__ == "__main__":
    main()
