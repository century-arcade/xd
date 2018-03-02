#!/usr/bin/env python

# Usage:
#   $0 <inputs>

# enumerates all answers/clues in the given inputs and writes them to the output .tsv

from xdfile.utils import get_args, open_output
from xdfile import corpus

def main():
    args = get_args("save all clues in simple .tsv")
    outf = open_output("clues.tsv")

    outf.write_row("PublicationId Date Answer Clue".split())
    for xd in corpus(*args.inputs):
        pubid = xd.publication_id
        dt = xd.date()
        for pos, clue, answer in xd.clues:
            outf.write_row((pubid or "", dt or "", answer, clue))

main()
