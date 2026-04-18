#!/usr/bin/env python3
#
# Usage: $0 <input>...
#
#   Scans .puz files for cryptic crossword indicators and writes a manifest
#   to stdout (TSV). Uses two signals in the .puz bytes:
#
#     grid  — pattern '.-.-.' in the fill grid (successive 1-cell across
#             slots, characteristic of cryptic lattice grids).
#     clue  — pattern '(\d+(,\d+)*)\x00' (null-terminated cryptic length
#             markers like "(5)" or "(3,4)" at clue ends).
#
#   Both signals present = high confidence. Grid only = needs review
#   (likely a themed American puzzle or a cryptic using non-numeric
#   clue annotations like "(ddef)").
#


import re
import sys
from xdfile.utils import progress, get_args, args_parser
import xdfile.utils


GRID_PAT = b'.-.-.'
CLUE_PAT = re.compile(rb'\(\d+(?:,\d+)*\)\x00')
CLUE_THRESHOLD = 5


def main():
    p = args_parser('scan .puz archive for cryptics; emit manifest TSV to stdout')
    args = get_args(parser=p)

    out = sys.stdout
    out.write("path\tconfidence\tgrid_hits\tclue_hits\n")

    for inputfn in args.inputs:
        for fn, contents, dt in xdfile.utils.find_files_with_time(inputfn):
            if not contents or not fn.endswith('.puz'):
                continue
            progress(fn)

            grid_hits = contents.count(GRID_PAT)
            if grid_hits == 0:
                continue

            clue_hits = len(CLUE_PAT.findall(contents))
            if clue_hits >= CLUE_THRESHOLD:
                confidence = 'high'
            else:
                confidence = 'review'
            out.write("%s\t%s\t%d\t%d\n" % (fn, confidence, grid_hits, clue_hits))


if __name__ == "__main__":
    main()
