#!/usr/bin/env python3

from xdfile.utils import get_args, parse_tsv, parse_pathname, open_output
from collections import namedtuple
from xdfile.metadatabase import Publication
from xdfile.html import html_header, html_footer, td, th, html_table, mkhref

# joins puzzles.tsv with similar.tsv, publications.tsv to make
#  xd.saul.pw/pub/up/index.html and /pub/up/2015/index.html

# /pub/<pubid>/<year>/index.html:

# one row per puzzle, clear links to that puzzle's analysis and/or proper
# place to play that puzzle online if available (does not pretend to link if
# it's not available)

# style analyzed rows differently

# remove 1A/1D spoiler if 'play' link available
# sidebar links to top, email, and all other publisher-years in sidebar

# include summary: # puzzles, date range, statistics on authors

def tsv_join(tsvgens):
    rows = {}
    fields = set()

    # first one defines which rows are in the set
    for r in tsvgens[0]:
        xdid = r.xdid
        assert xdid not in rows
        rows[xdid] = r._asdict()
        fields.update(set(r._fields))

    # then each gets expanded
    for tsv in tsvgens[1:]:
        for r in tsv:
            xdid = r.xdid
            if xdid in rows:
                rows[xdid].update(r._asdict())
                fields.update(set(r._fields))

    nt = namedtuple("superrow", " ".join(fields))
    for k, r in sorted(rows.items()):
        yield nt(**r)


def main():
    args = get_args('generate publication index')
    outf = open_output()

    all_pubs = {} # [pubid] -> Publication
    pubyears = {} # [pubid,year] -> html
    pubrows = {}

    pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', '1Across_1Down', 'SimilarGrids', 'ReusedClues', 'ReusedAnswers' ]

    for r in tsv_join([ parse_tsv(fn, parse_pathname(fn).base) for fn in args.inputs ]):
        pubid = r.PublicationAbbr
        year = r.Date.split('-')[0] or "unknown"
        if pubid not in all_pubs:
            all_pubs[pubid] = Publication(pubid)

        all_pubs[pubid].add(r)

        if pubid not in pubrows:
            pubrows[pubid] = [ ]

        if (pubid, year) not in pubyears:
            pubyears[(pubid, year)] = [ ]

        if r.similar_grid_pct != '0':
            similargrids = "%.1f" % (float(r.similar_grid_pct) / 100.0)
        else:
            similargrids = ""

        row = [ mkhref(r.xdid, "/pub/%s/%s/%s" % (pubid, year, r.xdid)),
                r.Date,
                r.Size,
                r.Title,
                r.Author,
                r.Editor,
                r.Copyright,
                r.A1_D1,
                similargrids,
                int(r.reused_clues) or "",
                int(r.reused_answers) or "",
              ]

        pubyears[(pubid, year)].append(row)
        pubrows[pubid].append(row)
           

    for (pubid, year), rows in sorted(pubyears.items()):
        opy = html_table(rows, pubyear_header)
        outf.write_html('pub/%s/%s/index.html' % (pubid, year), opy, title="%s %s (%d puzzles)" % (pubid, year, len(rows)))

    for pubid, pub in all_pubs.items():
        h = html_table([ pub.row() ], pub.meta())
        h += html_table(pubrows[pubid], pubyear_header)
        outf.write_html('pub/%s/index.html' % pubid, h, title=pubid)


main()
