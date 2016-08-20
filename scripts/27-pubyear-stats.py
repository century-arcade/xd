#!/usr/bin/env python3

import json
from collections import defaultdict, Counter

from xdfile import utils, metadatabase as metadb
from xdfile import year_from_date, dow_from_date
import xdfile


def main():
    args = utils.get_args('generate pub-years data')
    outf = utils.open_output()

    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]

    pubyears = set()
    for r in metasql.execute("SELECT * FROM puzzles"):
        pubyears.add(r.xdid.split("-")[0])


    for puby in pubyears:
        pubid, year = (puby)
        nxd = 0
        npublic = 0

        # SELECT FROM publications
        nexisting = 0

        # organize by day-of-week
        byweekday = {}
        byweekday_similar = {}
        for w in weekdays:
            byweekday[w] = []
            byweekday_similar[w] = []

        for r in metasql.execute("SELECT * FROM puzzles WHERE xdid LIKE '{}%'".format(puby)):
            byweekday[dow_from_date(r.Date)].append(r)

        for r in metasql.execute("SELECT * FROM similar_grids WHERE xdid LIKE '{}%' AND GridMatchPct > 25".format(puby)):

            byweekday_similar[dow_from_date(r.Date)].append(r)

        # tally stats
        for weekday in weekdays:
            copyrights = Counter()  # [copyright_text] -> number of xd
            editors = Counter()  # [editor_name] -> number of xd
            formats = Counter()  # ["15x15 RS"] -> number of xd
            # todo
            nexisting = 0

            for p in byweekday[weekday]:
                nxd += 1
                if p.xdid in public_xdids:
                    npublic += 1
                editors[p.Editor.strip()] += 1
                formats[p.Size.strip()] += 1
                copyrights[p.Copyright.strip()] += 1

            maineditor = "%s (%s)" % editors.most_common(1)[0]
            maincopyright = "%s (%s)" % copyrights.most_common(1)[0]
            mainformat = "%s (%s)" % formats.most_common(1)[0]

            reprints = 0
            touchups = 0
            redones = 0
            copies = 0
            themecopies = 0
            for r in byweekday_similar[weekday]:
                xd1 = corpus[r.xdid]
                xd2 = corpus[r.xdidMatch]
                dt1 = xd1.get_header('Date')
                dt2 = xd2.get_header('Date')
                aut1 = xd1.get_header('Author')
                aut2 = xd2.get_header('Author')
                pct = int(r.GridMatchPct)
                if dt2 < dt1:  # only capture the later one
                    if aut1 == aut2:
                        if pct == 100:
                            reprints += 1
                        elif pct >= 95:
                            touchups += 1
                        elif pct >= 30:
                            redones += 1
                    else: # suspicious
                        if pct > 50:
                            copies += 1
                        elif pct >= 30:
                            themecopies += 1

            metasql.execute("INSERT INTO stats VALUES (?,?,?, ?,?,?, ?, ?,?,?, ?,?, ?,?)",
            (pubid, year, weekday,
                mainformat, maineditor, maincopyright,
                nexisting, nxd, npublic,
                reprints, touchups, redones,
                copies, themecopies))


if __name__ == "__main__":
    main()
