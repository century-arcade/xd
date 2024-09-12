#!/usr/bin/python3

import re
import operator
import datetime
import string

from datetime import date
from xdfile.utils import info, debug, error
from xdfile import utils
from xdfile import metadatabase as metadb
from xdfile import html
from xdfile.utils import space_with_nbsp
import xdfile
from collections import defaultdict, OrderedDict

DECADE_SKIP_START = 1990
DECADE_SKIP_END = 1980


pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', '1Across_1Down', 'Similar Previous Grids' ]


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
<table class="legend">
<tr><td class="box pure">&nbsp;&nbsp;</td><td>100% grid match of an earlier puzzle, same author (reprint)</td></tr>
<tr><td class="box dupxd">&nbsp;&nbsp;</td><td>&gt;50% grid match of an earlier puzzle, same author</td></tr>
<tr><td class="box suspxd">&nbsp;&nbsp;</td><td>&gt;50% grid match of an earlier puzzle, different author</td></tr>
<tr><td class="box themexd">&nbsp;&nbsp;</td><td>25-50% grid match of an earlier puzzle (possible theme duplication)</td></tr>
</table>
<table class="legend">
<tr><td class="box pubxd">&nbsp;&nbsp;</td><td>crossword grid data available for <a href="/data#download">public download</a></td></tr>
<tr><td class="box privxd">&nbsp;&nbsp;</td><td>crossword grid data in private storage</td></tr>
</table>
<p style="clear:both">&nbsp;</p>
'''


def rect(x, y, w, h, *classes):
  return '<rect transform="translate({x},{y})" class="{classes}" width="{w}" height="{h}"></rect>\n'.format(x=int(x), y=int(y), w=int(w), h=int(h), classes=''.join(classes))


def year_from(dt):
    return int(dt.split('-')[0])


def weekdays_between(dta, dtb):
    return 0


def pubyear_svg(rows, height=svg_h, width=svg_w, pubid='', year=''):
    bgclass = 'notexists'

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
    NumRedone INTEGER,   -- 20-75% grid match
    -- duplicate grids, different author
    NumSuspicious INTEGER, -- >50% similar grid
    NumThemeCopies INTEGER -- >50% similar grid
    """
    row = utils.AttrDict(rows[0])
    svgtitle = '{} {}\n'.format(row.pubid, row.year)
    svgtitle += 'Copyright: {}\n'.format(row.Copyright) if row.Copyright else ''
    svgtitle += 'Editor: {}'.format(row.Editor) if row.Editor else ''

    for i, wd in enumerate(utils.WEEKDAYS): #range(0, 7):
        row = utils.AttrDict(rows[i])
        y = i*2 + 2
        num_existing = 52 if 's' not in year else 520 # (eventually number of this weekday in that year, *10 for decades)

        num_xd = int(row.NumXd)
        if num_xd > 0:
            bgclass = 'exists'

        #dup_length is length of dup/orange line
        num_dup = int(row.NumReprints) + int(row.NumTouchups) + int(row.NumRedone)

        # susp_length is length of suspicious/red line
        num_susp = int(row.NumSuspicious)
        num_theme = int(row.NumThemeCopies)
        # TODO: base color on suspicious vs theme (darker when only suspicious)

        num_pub = int(row.NumPublic)

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

        m = re.match(r'(\d+?)x(\d+?).*', row.Size)
        if m:
            sz = int(m.group(1)) * int(m.group(2))
            if sz > 17*17:
                h = 4
            else:
                h = 3
        else:
            h = 3

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
    href = "/pub/%s%s/index.html" % (pubid, year)
    ret = html.mkhref(pys.format(w=width,h=height,classes=bgclass,body=rects), href, svgtitle)
    return ret


def ret_classes(author1, author2, pct):
    # Return classes depends on authors and similarity pct
    ##deduce_similarity_type
    classes = ''
    author1 = boil(author1)
    author2 = boil(author2)
    if author1 and author2 and author1 not in author2 and author2 not in author1:# suspicious
        if abs(pct) >= 50:
            classes += ' suspxd'
        elif abs(pct) >= 20:
            classes += ' themexd'
    else:
        if abs(pct) == 100:
            classes += ' pure'
        elif abs(pct) >= 50:
            classes += ' dupxd'
        elif abs(pct) >= 20:
            classes += ' themexd'
    return classes


def gen_year_header(allyears):
    # Generate HTML year header
    # Table header with years \ decades
    year_header = []
    year_header.append('<tr><td>&nbsp;</td>')
    for year in sorted(allyears):
        if year[-1] == 's':
            lead = '19'
            yclass = 'decade'
        elif year[3] == '0':
            lead = year[:2]
            yclass = 'zero-year'
        else:
            lead = '&nbsp;'
            yclass = 'ord-year'
        year_header.append('<td class="{}">{}<br>{}</td>'.format(yclass, lead, year[2:]))
    year_header.append('</tr>')
    return year_header


def td_for_pubyear(pubyears, pub, year):
    py = pub + year
    if 's' not in year:
        # Process for single year
        if py in pubyears:
            return pubyear_svg(pubyears[py],pubid=pub,year=year)
    else:
        # Process for decade
        decade = []
        row_id = ['NumXd', 'NumReprints', 'NumTouchups', 'NumRedone', 'NumSuspicious', 'NumThemeCopies', 'NumPublic']
        for wdi, wd in enumerate(utils.WEEKDAYS):
            wd_dict = {
                    'weekday': wd,
                    'pubid': pub,
                    'year': year,
                    'Copyright': '',
                    'Editor': '',
                    'Size': '',
            }
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
        return pubyear_svg(decade, width=svg_w*decade_scale,year=year,pubid=pub) if decade else None

    return ''

def boil(x):
    return ''.join(c for c in x.lower() if c in string.ascii_lowercase)

def pubyear_html(pub, year):
    calendars_html = '<table class="puzzles">'
    colnames = [ year ] + pubyear_header
    calendars_html += html.table_row(colnames, colnames, tag='th')

    # write out /pub/nyt199x
    c_grids = {}

    # utils.info('Generating meta for {pub}{year}'.format(**locals()))
    for row in sorted(metadb.xd_similar(pub+year)):
        dt = utils.parse_iso8601(row.xdid)
        dt2 = utils.parse_iso8601(row.match_xdid)

        if not dt or not dt2:
            continue
        if dt < dt2:
            continue

        # dt = row["date"] # without - as GridCalendar needs; or fix GC
        if dt not in c_grids:
            c_grids[dt] = {
                'title': '',
                'class': ''
            }

        if row.match_pct == 0:
            continue

        c_grids[dt]['link'] = '/pub/' + row.xdid

        matchxdid = row.match_xdid
        aut1 = metadb.get_author(row.xdid) or ''
        aut2 = metadb.get_author(matchxdid) or ''
#        if aut1 is None or aut2 is None:
#            continue

        pct = row.match_pct
        similargrids = '(%s%%) %s [%s]\n' % (pct, aut2, matchxdid)
        c_grids[dt]["title"] += similargrids

        ##deduce_similarity_type
        c_grids[dt]["class"] += ret_classes(aut1, aut2, pct)

    c_grids_b = {}  #  For those are not in c_grids

    # Generate grids for available puzzles
    for row in metadb.xd_puzzles(pub+year):
        if row.Date and row.Date not in c_grids_b and row.Date not in c_grids:
            # add styles only for those are not similar etc.
            c_grids_b[row.Date] = {
                'title': '',
                'class': 'privxd' if int(row.Date[:4]) > 1965 else 'pubxd',
            }

    # Generate calendars
    z = c_grids.copy()
    z.update(c_grids_b)

    if year[-1] == 's':  # decade
        from_year = int(year[:4])
        to_year = int(year[:4]) + 10
    else:
        from_year = int(year)
        to_year = int(year) + 1

    for year in range(from_year, to_year):
      for month in range(1, 13):
        dups_table = []
        for dt, d in c_grids.items():
            if not dt.startswith("%s-%02d" % (year, month)):
                continue

            row_dict = {}  # Map row and style
            xdid = pub + dt
            puzmd = metadb.xd_puzzle(xdid)
            if not puzmd:
                continue
            row_dict['class'] = d['class']
            row_dict['tag_params'] = {
                'onclick': 'location.href=\'/pub/%s\'' % xdid,
                'class': d['class'] + ' hrefrow puzrow',
            }
            row_dict['row'] = [
                xdid,
                puzmd.Date,
                puzmd.Size,
                puzmd.Title,
                puzmd.Author,
                puzmd.Editor,
                puzmd.Copyright,
                puzmd.A1_D1,
                d["title"].replace("\n", "<br/>")
            ]
            dups_table.append(row_dict)

        calendars_html += '<tr class="calendar"><td class="calendar" rowspan="%s">' % (len(dups_table) + 1)
        calendars_html += html.GridCalendar(z).formatmonth(int(year), month) + '</td></tr>'

        for r in sorted(dups_table, key=lambda x: x['row'][1]):
            calendars_html += html.table_row(r["row"], pubyear_header, tag_params=r['tag_params'])

    calendars_html += '</table>'

    ret = '''%s <div class="calendars">%s</div> <hr/>''' % (legend, calendars_html)
    return ret


def main():
    p = utils.args_parser(desc="generate pubyear svg and pubyear pages")
    p.add_argument('-p', '--pubonly', action="store_true", default=False, help='only output root map')
    args = utils.get_args(parser=p)
    outf = utils.open_output()

    pubyears = defaultdict(list)
    pubyears_idx = defaultdict(list)
    # years_idx = []
    for r in metadb.read_rows('pub/stats'):
        y = r.year or '0000'
        pubyear = r.pubid + str(y)
        pubyears[pubyear].append(r)
        if y not in pubyears_idx[r.pubid]:
            pubyears_idx[r.pubid].append(y)
        # if r.year not in years_idx:
        #    years_idx.append(r.year)

    # Making collapsed decades depends on args
    allyears = []
    for i in range(DECADE_SKIP_START//10, DECADE_SKIP_END//10 + 1):
        allyears.append("%s0s" % i)
    allyears.extend([ str(y) for y in range(DECADE_SKIP_END + 10, date.today().year + 1) ])

    html_out = []
    html_out.append('<p>Grouped by publication-year and broken out by day-of-week (Monday at top, Sunday at bottom).</p>')
    html_out.append(legend) # See definition above
    html_out.append('<table id="pubyearmap" cellspacing="0" cellpadding="0">')

    # Table header with years \ decades
    year_header = gen_year_header(allyears)
    html_out.extend(year_header)

    pubs_total = {}
    for pubid in pubyears_idx:
        pubs_total[pubid] = len(metadb.xd_puzzles(pubid))

    # sort rows by number of puzzles
    sorted_pubs = sorted(pubs_total.keys(), key=lambda pubid: pubs_total[pubid], reverse=True)
    for pub in args.inputs or sorted_pubs:
        if pubs_total[pub] < 20:
            continue

        # Process each pub in index
        pubobj = metadb.xd_publications().get(pub)
        if pubobj:
            pubname = pubobj.PublicationName or pubobj.PublisherName
        else:
            pubname = pub
        html_out.append('<tr><td class="header">{}</td>'.format(html.mkhref(pubname, 'pub/' + pub)))

        for year in sorted(allyears):
            html_out.append('<td class="year_widget">')
            py_td = td_for_pubyear(pubyears, pub, year)
            if py_td:
                html_out.append(py_td)
                if not args.pubonly:
                    outf.write_html('pub/{pub}{year}/index.html'.format(**locals()), pubyear_html(pub, year),
                                    "{pubname}, {year}".format(**locals()))
            else:
                # otherwise
                width = svg_w if 's' not in year else svg_w*decade_scale
                html_out.append(pys.format(w=width, h=svg_h, title='', classes='notexists', body=''))

            html_out.append('</td>')

        # Add totals + publishers
        html_out.append('<td class="header">{}</td>'.format(pubs_total[pub]))
        html_out.append('<td class="header">{}</td>'.format(html.mkhref(pubname, 'pub/' + pub)))
        html_out.append('</tr>')


    html_out.extend(year_header)
    html_out.append('</table>')
    total_xd = len(metadb.xd_puzzles())
    outf.write_html('index.html', "".join(html_out), "Comparison of %s published crossword grids" % total_xd)


if __name__ == "__main__":
    main()
