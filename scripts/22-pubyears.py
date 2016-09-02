#!/usr/bin/env python3

import json
from collections import defaultdict

from xdfile import utils, metadatabase as metadb, metasql
from xdfile import year_from_date, dow_from_date
import xdfile


def main():
    args = utils.get_args('generate pub-years data')
    
    puzzles = metasql.select('SELECT * FROM puzzles;')

    pubyears = [ (utils.parse_pubid(r['xdid']), year_from_date(r['Date']), dow_from_date(r['Date']))
					for r in puzzles]
    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]
    pubs = defaultdict(dict)
    for pubid, year, dow  in pubyears:
        if pubid not in pubs or int(year) not in pubs[pubid]:
            pubs[pubid][int(year)] = { k:0 for k in weekdays }
        if dow:
            pubs[pubid][int(year)][dow] += 1

    outf = utils.open_output()

    for pubid, years_dow in pubs.items():
        for y in sorted(years_dow.keys()):
            if y < 1900 or y > 2100:
                continue
            # Preserve weekday order
            dow_list = []
            for d in weekdays:
                dow_list.append(str(years_dow[y][d]))

            metadb.append_row('pub/pubyears.tsv', "pubid year total " + " ".join(weekdays),
                    [ pubid, y, sum(years_dow[y].values()), "\t".join(dow_list) ])

if __name__ == "__main__":
    main()
