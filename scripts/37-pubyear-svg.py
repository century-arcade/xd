#!/usr/bin/python3

import re
import operator
import datetime

from datetime import date
from xdfile.utils import info, debug, error
from xdfile import utils
from xdfile import metadatabase as metadb
from xdfile import html
from xdfile.utils import space_with_nbsp
import xdfile
from collections import defaultdict, OrderedDict

DECADE_SKIP_START = 1910
DECADE_SKIP_END = 1980


pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', '1Across_1Down', 'Similar Grids' ]


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
<tr><td class="themexd">&nbsp;&nbsp;</td><td>25-50% grid match of an earlier puzzle (likely theme copy)</td></tr>
<tr><td class="suspxd">&nbsp;&nbsp;</td><td>50%+ grid match of an earlier puzzle, different author</td></tr>
<tr><td class="dupxd">&nbsp;&nbsp;</td><td>50%+ grid match of an earlier puzzle, same author (reprint/resubmission)</td></tr>
</table>
<table class="legend">
<tr><td class="pubxd">&nbsp;&nbsp;</td><td>crossword grid data available for <a href="/download">public download</a></td></tr>
<!--tr><td class="privxd">&nbsp;&nbsp;</td><td>crossword grid data in private storage</td></tr-->
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
    href = "/pub/%s%sx/index.html#%s" % (pubid, year[:3], year)
    ret = html.mkhref(pys.format(w=width,h=height,classes=bgclass,body=rects), href, svgtitle)
    return ret


def ret_classes(author1, author2, pct):
    # Return classes depends on authors and similarity pct
    ##deduce_similarity_type
    classes = ''
    if author1 and author2 and author1.lower() != author2.lower():# suspicious
        if pct >= 50:
            classes += ' suspxd'
        elif pct >= 20:
            classes += ' themexd'
    else:
        if pct == 100:
            classes += ' white'
        elif pct >= 50:
            classes += ' dupxd'
        elif pct >= 20:
            classes += ' themexd'
    return classes


def gen_year_header(allyears):
    # Generate HTML year header
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


def pubdecade_html(pub, year):
    calendars_html = ''
    dups_table = []

    # write out /pub/nyt199x
    decade = year[:3]
    c_grids = {}

    # utils.info('Generating meta for pub:{pub} decade:{decade}0'.format(**locals()))
    for row in sorted(metadb.xd_similar(pub+decade)):
        m = re.match(r'^\w+(\d{4}-\d{2}-\d{2})', row.xdid)
        if m:
            dt = m.group(1)
        else:
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
        aut1 = metadb.get_author(row.xdid)
        aut2 = metadb.get_author(matchxdid)
        if aut1 is None or aut2 is None:
            continue

        pct = row.match_pct
        similargrids = '(%s%%) %s [%s]\n' % (pct, aut2, matchxdid)
        c_grids[dt]["title"] += similargrids

        ##deduce_similarity_type
        c_grids[dt]["class"] = ret_classes(aut1, aut2, pct)

    c_grids_b = {}  #  For those are not in c_grids

    cur_year = datetime.datetime.now().year
    from_year = int(decade + '0')
    to_year = min(cur_year, from_year + 9)
    puzzles_by_year = dict((y, 0) for y in range(from_year, to_year+1))

    # Generate grids for available puzzles
    for row in metadb.xd_puzzles(pub+decade):
        if row.Date and row.Date not in c_grids_b and row.Date not in c_grids:
            # add styles only for those are not similar etc.
            c_grids_b[row.Date] = {
                'title': '',
                'class': 'privxd' if int(row.Date[:4]) > 1965 else 'pubxd',
            }
        puzzles_by_year[int(row.Date.split('-')[0])] += 1

    # Generate calendars
    z = c_grids.copy()
    z.update(c_grids_b)
    for year in range(from_year, to_year+1):
        if puzzles_by_year[year] == 0:
            continue

        calendars_html += html.GridCalendar(z).formatyear(year, 6) + "<br>"

    for dt, d in c_grids.items():
        row_dict = {} # Map row and style
        xdid = pub + dt
        puzmd = metadb.xd_puzzle(xdid)
        if not puzmd:
            continue
        row_dict['class'] = d['class']
        row_dict['tag_params'] = {
            'onclick': 'location.href=\'/pub/%s\'' % xdid,
            'class' : d['class'] + ' hrefrow',
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

    ret = '''%s <div class="calendars">%s</div> <hr/>''' % (legend, calendars_html)
    ret += html.html_table(sorted(dups_table, key=lambda x: x['row'][1]), pubyear_header, "puzzle", "puzzles")
    return ret


def main():
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', action="store_true", default=False, help='analyze all puzzles, even those already in similar.tsv')
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

    # sort rows by most recent puzzle in collection, then by pubid
    sorted_idx = OrderedDict(sorted(pubyears_idx.items(), key=lambda r: (-int(max(r[1])), r[0])))
    for pub in sorted_idx:
        if pubs_total[pub] < 20:
            continue

        # Process each pub in index
        pubobj = metadb.xd_publications().get(pub)
        if pubobj:
            pubname = pubobj.PublicationName or pubobj.PublisherName
        else:
            pubname = pub
        html_out.append('<tr><td class="header">{}</td>'.format(html.mkhref(pubname, pub)))

        for year in sorted(allyears):
            html_out.append('<td class="year_widget">')
            py_td = td_for_pubyear(pubyears, pub, year)
            if py_td:
                html_out.append(py_td)
                if not args.pubonly and year[3:4]=='0':
                    decade = year[0:3]
                    cur_year = datetime.datetime.now().year
                    from_year = int(decade + '0')
                    to_year = min(cur_year, from_year + 9)
                    outf.write_html('pub/{pub}{decade}x/index.html'.format(**locals()), pubdecade_html(pub, year),
                            "{pubname}, {from_year}-{to_year}".format(**locals()))
            else:
                # otherwise
                width = svg_w if 's' not in year else svg_w*decade_scale
                html_out.append(pys.format(w=width,h=svg_h, title='', classes='notexists', body=''))

            html_out.append('</td>')

        # Add totals + publishers
        html_out.append('<td class="header">{}</td>'.format(pubs_total[pub]))
        html_out.append('<td class="header">{}</td>'.format(html.mkhref(pubname, pub)))
        html_out.append('</tr>')

    html_out.extend(year_header)
    html_out.append('</table>')
    total_xd = len(metadb.xd_puzzles())
    outf.write_html('index.html', "".join(html_out), "Comparison of %s published crossword grids" % total_xd)


if __name__ == "__main__":
    main()
