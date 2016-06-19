#!/usr/bin/env python3

import json
from collections import Counter

from xdfile import utils, metadatabase as metadb
import xdfile


# pub/pubyears.tsv:
"""
   SELECT pubid,
          year_from_date(date) AS year,
          COUNT(*) AS num
      FROM puzzles
      GROUP BY pubid, year
      WHERE year > 1900 AND year < 2100
"""

def main():
    args = utils.get_args('generate pub-years data')

#    pubyears = [ (xd.publication_id(), xd.year()) for xd in xdfile.corpus() ]
    pubyears = [ (utils.parse_pubid(r.xdid), xdfile.year_from_date(r.Date)) 
					for r in metadb.xd_puzzles().values() ]

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
            if y < 1900 or y > 2100:
                continue
            metadb.append_row('pub/pubyears.tsv', "pubid year num", [ pubid, y, years[y] ])

main()


