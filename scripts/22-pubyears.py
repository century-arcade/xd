#!/usr/bin/env python3

import json
from collections import defaultdict

from xdfile import utils, metadatabase as metadb
from xdfile import year_from_date, dow_from_date
import xdfile


def main():
    args = utils.get_args('generate pub-years data')

    pubyears = [ (utils.parse_pubid(r.xdid), year_from_date(r.Date), dow_from_date(r.Date)) 
                    for r in metadb.xd_puzzles().values() ]

    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]

    metasql.execute("INSERT INTO stats VALUES (?,?,?, ?,?, ?, ?,?,?, ?,?, ?,?)",
            (pubid, year, weekday,
                maineditor, maincopyright,
                nexisting, nxd, npublic,
                reprints, touchups, redones,
                copies, themecopies))





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
            for d in weekdays:
                ndup = 0
                nsusp = 0
                for r in metasql.xd_similar():
                    "SELECT * FROM similar WHERE pubid = ? AND year = ?", pubid, y)
                ("INSERT INTO pubyears VALUES (?, ?, ?, ?, ?)metadb.append_row('pub/pubyears.tsv', "pubid year weekday total ndup nsusp",
                    [ pubid, y, d, years_dow[y][d], ndup, nsusp])

if __name__ == "__main__":
    main()
