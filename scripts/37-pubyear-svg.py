#!/usr/bin/python3

import re

from datetime import date
from xdfile import utils
from xdfile import metasql as metadb
import xdfile


pys = '''
<svg class="year_widget" width="30" height="30">
  <title>%s</title>
  <g transform="translate(0,0)">
    <rect class="%s" width="30" height="30"></eect>
  </g>
%s
</svg>
'''


def rect(x, y, w, h, *classes):
  return '<rect transform="translate({x},{y})" class="{classes}" width="{w}" height="{h}"></rect>'.format(x=int(x), y=int(y), w=int(w), h=int(h), classes=''.join(classes))


def year_from(dt):
    return int(dt.split('-')[0])

def weekdays_between(dta, dtb):
    return 0


def pubyear_svg(row): #, nsusp, ndup, npub, npriv):
    bgclass = "notexists"
#    if bgclass not in publications.tsv:
#       bgclass = "exists"

    rects = ''
    """
    pubid CHAR(6),   -- "nyt"
    year CHAR(4),    -- "2006"
    weekday CHAR(3), -- "Mon"
    Size TEXT, -- most common entry
    Editor TEXT, -- most common entry
    Copyright TEXT, -- most common, after removing Date/Author
    NumExisting INTEGER, -- known or assumed to be in existence (0 means unknown)
    NumXd INTEGER,       -- total number in xd
    NumPublic INTEGER,   -- available for public download
    -- duplicate grids, same author
    NumReprints INTEGER, -- 100% grid match
    NumTouchups INTEGER, -- 75-99% grid match
    NumRedone INTEGER,   -- 30-75% grid match
    -- duplicate grids, different author
    NumSuspicious INTEGER, -- >50% similar grid
    NumThemeCopies INTEGER -- >50% similar grid
    """

    svgtitle = '{} {}\n'.format(row['pubid'], row['year'])
    svgtitle += 'Copyright: {}\n'.format(row['Copyright']) if row['Copyright'] else ''
    svgtitle += 'Editor: {}'.format(row['Editor']) if row['Editor'] else ''

    for i in range(0, 7):
        y = i*3

        num_existing = 52 # (eventually number of this weekday in that year)

        num_xd = row["NumXd"]

        #dup_length is length of dup/orange line
        num_dup = row['NumReprints'] + row['NumTouchups'] + row['NumRedone']

        # susp_length is length of suspicious/red line
        num_susp = row['NumSuspicious'] + row['NumThemeCopies']
        # TODO: base color on suspicious vs theme (darker when only suspicious)

        num_pub = row['NumPublic']

        num_priv = num_xd - num_pub

        pixel_prexd = 0
        pixel_postxd = 0
        if num_xd < num_existing:
            # for now; eventually should use earliest/latest date and puzzle to determine which side has gap
            # npre = weekdays_between(date(year_from(firstxd.Date), 1, 1), firstxd.Date, i)
            # npost = weekdays_between(lastxd.Date, date(year_from(lastxd.Date), 12, 31), i)
            pixel_prexd = 1
            pixel_postxd = 1

        pixel_total = 30 - pixel_prexd - pixel_postxd

        # then convert num_* to pixel_*, num_existing to pixel_total
        pixel_susp = num_susp*pixel_total/num_existing
        pixel_dup = num_dup*pixel_total/num_existing
        pixel_pub = num_pub*pixel_total/num_existing
        pixel_priv = num_priv*pixel_total/num_existing

        m = re.match(r'(\d+?)x(\d+?).*', row['Size'])
        if m:
            sz = int(m.group(1)) * int(m.group(2))
            if sz > 17*17:
                h = 3
            else:
                h = 2
        else:
            h = 1

        x = 0
        w = 6
        rects += '''<g id="{}" transform="translate(0,{y})">'''.format(utils.WEEKDAYS[i],y=int(y))

        w = pixel_prexd
        rects += rect(x, y, w, h, 'prexd')
        x += w

        w = pixel_susp
        rects += rect(x, y, w, h, 'suspxd')
        x += w

        w = pixel_dup
        rects += rect(x, y, w, h, 'dupxd')
        x += w

        w = pixel_priv
        rects += rect(x, y, w, h, 'privxd')
        x += w

        w = pixel_pub
        rects += rect(x, y, w, h, 'pubxd')
        x += w

        w = pixel_postxd
        rects += rect(x, y, w, h, 'postxd')
        rects += '</g>'

    return pys % (svgtitle, bgclass, rects)


def main():
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', default=False, help='analyze all puzzles, even those already in similar.tsv')
    args = utils.get_args(parser=p)
    outf = utils.open_output()

    pubyears = {}
    for r in metadb.select("SELECT * FROM stats"):
        pubyear = r['pubid'] + r['year']
        pubyears[pubyear] = r
    html_out = []
    for py in sorted(pubyears):
        html_out.append(pubyear_svg(pubyears[py]))
    outf.write_html('svg.html', "".join(html_out), "Total svg")


if __name__ == "__main__":
    main()

