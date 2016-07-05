#!/usr/bin/env python3

from xdfile import utils
import xdfile

args = utils.get_args('make clues.tsv files')
outf = utils.open_output()
for ca in xdfile.clues():
    outf.write_row('clues-%s.tsv' % ca.pubid, "year answer clue", [xdfile.year_from_date(ca.date), ca.answer, ca.clue])

def every_clue(ca):
    write_row('pub/clues-%s.tsv' % ca.pubid, "year answer clue", [ca.year, ca.answer, ca.clue])
    write_row('priv/clues-%s.tsv' % ca.pubid, "xdid answer clue", [ca.xdid, ca.answer, ca.clue])
