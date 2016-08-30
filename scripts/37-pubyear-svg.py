#!/usr/bin/python3

import re
import operator

from datetime import date
from xdfile import utils
from xdfile import metasql as metadb
from xdfile import html
from xdfile.utils import space_with_nbsp
import xdfile
from collections import defaultdict, OrderedDict


svg_w = 32
svg_h = 35
decade_scale=1.3

pys = '''
<svg class="year_widget" width="{w}px" height="{h}px">
  <g transform="translate(0,0)">
    <rect class="{classes}" width="{w}px" height="{h}px"></rect>
  </g>
{body}
</svg>
'''

legend = '''
Broken out by day-of-week (Monday at top, Sunday at bottom).  Thicker lines mean larger puzzles.
<table>
<tr><td class="dupxd">&nbsp;&nbsp;</td><td>50%+ grid match of an earlier puzzle, same author (reprint/resubmission)</td></tr>
<tr><td class="themexd">&nbsp;&nbsp;</td><td>30-50% grid match of an earlier puzzle (likely theme copy)</td></tr>
<tr><td class="suspxd">&nbsp;&nbsp;</td><td>50%+ grid match of an earlier puzzle, different author (suspicious)</td></tr>
<tr><td><hr/></td></tr>
<tr><td class="pubxd">&nbsp;&nbsp;</td><td>crosswords available for <a href="/download">public download</a></td></tr>
<tr><td class="privxd">&nbsp;&nbsp;</td><td>crosswords currently not publicly available</td></tr>
</table>
<hr/>
'''


def rect(x, y, w, h, *classes):
  return '<rect transform="translate({x},{y})" class="{classes}" width="{w}" height="{h}"></rect>\n'.format(x=int(x), y=int(y), w=int(w), h=int(h), classes=''.join(classes))


def year_from(dt):
    return int(dt.split('-')[0])


def weekdays_between(dta, dtb):
    return 0


def pubyear_svg(rows, height=svg_h, width=svg_w, pubid='', year=''): #, nsusp, ndup, npub, npriv):
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
    row = rows[0]
    svgtitle = '{} {}\n'.format(row['pubid'], row['year'])
    svgtitle += 'Copyright: {}\n'.format(row['Copyright']) if row['Copyright'] else ''
    svgtitle += 'Editor: {}'.format(row['Editor']) if row['Editor'] else ''

    for i, wd in enumerate(utils.WEEKDAYS): #range(0, 7):
        row = rows[i]
        y = i*2 + 2
        num_existing = 52 if 's' not in year else 520 # (eventually number of this weekday in that year, *10 for decades)

        num_xd = row["NumXd"]

        if num_xd < 20:
            continue

        #dup_length is length of dup/orange line
        num_dup = row['NumReprints'] + row['NumTouchups'] + row['NumRedone']

        # susp_length is length of suspicious/red line
        num_susp = row['NumSuspicious']
        num_theme = row['NumThemeCopies']
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

        if not num_xd or not num_existing:
            continue

        pixel_total = width - pixel_prexd - pixel_postxd

        if num_xd <= num_existing:
            pixel_xd = pixel_total * num_xd / num_existing
        else:
            pixel_xd = pixel_total

        # then convert num_* to pixel_*, num_existing to pixel_total
        pixel_susp = num_susp*pixel_xd/num_xd
        pixel_theme = num_theme*pixel_xd/num_xd
        pixel_dup = num_dup*pixel_xd/num_xd
        pixel_pub = num_pub*pixel_xd/num_xd
        pixel_priv = num_priv*pixel_xd/num_xd

        if pixel_theme > 0 and pixel_theme < 1:
            pixel_theme = 1
        if pixel_susp > 0 and pixel_susp < 1:
            pixel_susp = 1
        if pixel_dup > 0 and pixel_dup < 1:
            pixel_dup = 1

        m = re.match(r'(\d+?)x(\d+?).*', row['Size'])
        if m:
            sz = int(m.group(1)) * int(m.group(2))
            if sz > 17*17:
                h = 4
            else:
                h = 1.5
        else:
            h = 1

        x = 0
        w = 6
        rects += '''<g id="{}" transform="translate(0,{y})">'''.format(utils.WEEKDAYS[i],y=int(y))

        w = pixel_prexd
#        rects += rect(x, y, w, h, 'prexd')
        x += w

        w = pixel_susp
        rects += rect(x, y, w, h, 'suspxd')
        x += w

        w = pixel_theme
        rects += rect(x, y, w, h, 'themexd')
        x += w

        w = pixel_dup
        rects += rect(x, y, w, h, 'dupxd')
        x += w

        if x <= pixel_total:
            w = min(pixel_total - x, max(0, pixel_priv))
            rects += rect(x, y, w, h, 'privxd')
            x += w

        if x <= pixel_total:
            w = min(pixel_total - x, max(0, pixel_pub))
            rects += rect(x, y, w, h, 'pubxd')
            x += w

#        w = pixel_postxd
#        rects += rect(x, y, w, h, 'postxd')
        rects += '</g>'
    href = "/pub/%s%s" % (pubid, year) if 's' not in year else "/pub/%s/index.html#%s" % (pubid, year[:-1])
    ret = html.mkhref(pys.format(w=width,h=height,classes=bgclass,body=rects), href, svgtitle)
    return ret


def main():
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', default=False, help='analyze all puzzles, even those already in similar.tsv')
    args = utils.get_args(parser=p)
    outf = utils.open_output()

    pubyears = defaultdict(list)
    pubyears_idx = defaultdict(list)
    # years_idx = []
    for r in metadb.select("SELECT * FROM stats"):
        y = r['year'] or '9999'
        pubyear = r['pubid'] + y
        pubyears[pubyear].append(r)
        if y not in pubyears_idx[r['pubid']]:
            pubyears_idx[r['pubid']].append(y)
        # if r['year'] not in years_idx:
        #    years_idx.append(r['year'])

    # Making collapsed decades depends on args
    skip_decades = None
    skip_decades = skip_decades if skip_decades else { 'start': 1910, 'end': 1980 } 
    allyears = []
    for i in range(skip_decades['start']//10, skip_decades['end']//10 + 1):
        allyears.append("%s0s" % i)
    allyears.extend([ str(y) for y in range(skip_decades['end'] + 10, date.today().year + 1) ])

    html_out = []
    html_out.append(legend)
    html_out.append('<table id="pubyearmap" cellspacing="0" cellpadding="0">')

    # Table header with years \ decades
    year_header = []
    year_header.append('<tr><td>&nbsp;</td>')
    for year in sorted(allyears):
        if year[-1] == 's':
            lead = ''
            yclass = 'decade'
        elif year[3] == '0':
            lead = year[:2]
            yclass = 'zero-year'
        else:
            lead = '&nbsp;'
            yclass = 'ord-year'
        year_header.append('<td class="{}">{}<br>{}</td>'.format(yclass, lead, year[2:]))
    year_header.append('</tr>')
    html_out.extend(year_header)

    sorted_idx = OrderedDict(sorted(pubyears_idx.items(), key=lambda r: min(r[1])))
    for pub in sorted_idx:
        # Process each pub in index
        pubobj = metadb.xd_publications().get(pub)
        if pubobj:
            pubname = pubobj.PublicationName or pubobj.PublisherName
        else:
            pubname = pub
        html_out.append('<tr><td class="header">{}</td>'.format(html.mkhref(pubname, pub)))
        for year in sorted(allyears):
            py = pub + year
            py_svg = None
            html_out.append('<td class="year_widget">')
            if 's' not in year:
                # Process for single year
                if py in pubyears:
                    py_svg = pubyear_svg(pubyears[py],pubid=pub,year=year)
            else:
                # Process for decade
                decade = []
                row_id = ['NumXd', 'NumReprints', 'NumTouchups', 'NumRedone', 'NumSuspicious', 'NumThemeCopies', 'NumPublic']
                for wdi, wd in enumerate(utils.WEEKDAYS):
                    wd_dict = {}
                    wd_dict['weekday'] = wd
                    wd_dict['pubid'] = pub
                    wd_dict['year'] = year
                    wd_dict['Copyright'] = ''
                    wd_dict['Editor'] = ''
                    wd_dict['Size'] = ''
                    for dec_year in [year[:3]+str(y) for y in range(0,10)]:
                        for rid in row_id:
                            if pubyears[pub+dec_year]:
                                if rid in wd_dict:
                                    wd_dict[rid] += pubyears[pub+dec_year][wdi][rid]
                                else:
                                    wd_dict[rid] = pubyears[pub+dec_year][wdi][rid]
                    # Emulate 7 rows per decade
                    if row_id[0] in wd_dict:
                        decade.append(wd_dict)
                py_svg = pubyear_svg(decade, width=svg_w*decade_scale,year=year,pubid=pub) if decade else None

            if py_svg:
                html_out.append(py_svg)
            else:
                width = svg_w if 's' not in year else svg_w*decade_scale
                html_out.append(pys.format(w=width,h=svg_h, title='', classes='notexists', body=''))

            html_out.append('</td>')
        # Add publishers
        html_out.append('<td class="header">{}</td>'.format(html.mkhref(pubname, pub)))
        html_out.append('</tr>')

    html_out.extend(year_header)
    html_out.append('</table>')
    outf.write_html('pub/index.html', "".join(html_out), "Published crosswords by year")


if __name__ == "__main__":
    main()

