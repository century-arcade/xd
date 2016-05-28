#!/usr/bin/env python3

import json
from collections import Counter

from xdfile import utils, metadatabase
import xdfile

def main():
    args = utils.get_args('generate pub-years data')

#    pubyears = [ (xd.publication_id(), xd.year()) for xd in xdfile.corpus() ]
    pubyears = [ (r.PublicationAbbr, xdfile.year_from_date(r.Date)) for r in metadatabase.xd_puzzles() ]

    pubs = {}
    for pubid, year in pubyears:
        if pubid not in pubs:
            pubs[pubid] = Counter()
        try:
            pubs[pubid][int(year)] += 1
        except:
            pass

    outf = utils.open_output()

    for pubid, years in pubs.items():
        for y in sorted(years.keys()):
            outf.write_row('pubyears.tsv', "pubid year num", [ pubid, y, years[y] ])

main()


