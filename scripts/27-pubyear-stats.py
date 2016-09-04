#!/usr/bin/env python3

import json
import re
from collections import defaultdict, Counter

from xdfile.utils import error, debug, info
from xdfile import utils, metasql, metadatabase as metadb
from xdfile import year_from_date, dow_from_date
import xdfile



def main():
    args = utils.get_args('generate pub-years data')
    outf = utils.open_output()

    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]

    pubyears = {} # set()
    for xd in xdfile.corpus():
        puby = (xd.publication_id(), xd.year())
        if puby not in pubyears:
            pubyears[puby] = []
        pubyears[puby].append(xd)

    if pubyears:
        metasql.execute("DELETE FROM stats;")

    for puby, xdlist in sorted(pubyears.items()):
        pubid, year = puby
        npublic = 0

        # TODO: SELECT FROM publications
        nexisting = 0

        # organize by day-of-week
        byweekday = {}
        byweekday_similar = {}
        for w in weekdays:
            byweekday[w] = []
            byweekday_similar[w] = []

        for xd in xdlist:
            dow = dow_from_date(xd.get_header('Date'))
            if dow: # Might be empty date or only a year
                byweekday[dow].append(xd)

        for r in metasql.select("SELECT * FROM similar_grids WHERE xdid LIKE '{}%' AND GridMatchPct > 25".format(pubid + str(year))):
            xd = xdfile.get_xd(r['xdid'])
            if xd:
                dt = xd.get_header('Date')
                if dt:
                    assert dt
                    dow = dow_from_date(dt)
                    if dow: # Might be empty date or only a year
                        byweekday_similar[dow].append(r)
                else:
                    debug("Date not set for: %s" % xd)

        # tally stats
        for weekday in weekdays:
            copyrights = Counter()  # [copyright_text] -> number of xd
            editors = Counter()  # [editor_name] -> number of xd
            formats = Counter()  # ["15x15 RS"] -> number of xd
            # todo
            nexisting = 0

            nxd = len(byweekday[weekday])
            public_xdids = [] # Empty for now
            for xd in byweekday[weekday]:
                xdid = xd.xdid()
                if  (year.isdigit() and int(year) <= 1965) or xdid in public_xdids:
                    npublic += 1

                editor = xd.get_header('Editor').strip()
                if editor:
                    editors[editor] += 1

                sizestr = xd.sizestr()
                if sizestr:
                    formats[sizestr] += 1

                copyright = xd.get_header('Copyright').strip()
                if copyright:
                    copyrights[copyright] += 1

            # debug("ME: %s MCPR: %s MF: %s" % (list(editors), list(copyrights), list(formats)))
            def process_counter(count, comp_value):
                # Process counter comparing with comp_value
                if count:
                    item, num  = count.most_common(1)[0]
                    if num != comp_value:
                        item += " (%s)" % num
                else:
                    item = ''
                return item

            #
            maineditor = process_counter(editors, nxd)
            maincopyright = process_counter(copyrights, nxd)
            mainformat = process_counter(formats, nxd)

            reprints = 0
            touchups = 0
            redones = 0
            copies = 0
            themecopies = 0
            for r in byweekday_similar[weekday]:
                # debug("Xdid %s Xdidmatch %s" % (r['xdid'], r['xdidMatch']))
                xd1 = xdfile.get_xd(r['xdid'])
                xd2 = xdfile.get_xd(r['xdidMatch'])
                if xd1 is None or xd2 is None:
                    continue
                # debug("XD1: %s XD2: %s" % (xd1, xd2))
                dt1 = xd1.get_header('Date')
                dt2 = xd2.get_header('Date')
                aut1 = xd1.get_header('Author')
                aut2 = xd2.get_header('Author')
                pct = int(r['GridMatchPct'])
                if dt2 < dt1:  # only capture the later one
                    ##deduce_similarity_type
                    if aut1 and aut2 and aut1 != aut2:# suspicious
                        if pct >= 50:
                            copies += 1
                        elif pct >= 30:
                            themecopies += 1
                    else: 
                        if pct == 100:
                            reprints += 1
                        elif pct >= 50:
                            touchups += 1
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
