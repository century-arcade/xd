#!/usr/bin/env python3

from collections import Counter, defaultdict
import re

from xdfile.utils import progress, open_output, get_args, args_parser, COLUMN_SEPARATOR
from xdfile import html, utils, catalog, pubyear
from xdfile import metadatabase as metadb
from xdfile.html import GridCalendar, mktag, year_widget
from xdfile.xdfile import num_cells
import xdfile


class PublicationStats:
    def __init__(self, pubid):
        self.pubid = pubid
        self.copyrights = Counter()  # [copyright_text] -> number of xd
        self.editors = Counter()  # [editor_name] -> number of xd
        self.formats = Counter()  # ["15x15 RS"] -> number of xd
        self.mindate = ""
        self.maxdate = ""
        self.num_xd = 0

        self.puzzles_meta = []

    def add(self, puzrow):
        self.copyrights[puzrow.Copyright.strip()] += 1
        self.editors[puzrow.Editor.strip()] += 1
        self.formats[puzrow.Size] += 1
        datestr = puzrow.Date
        if datestr:
            if not self.mindate:
                self.mindate = datestr
            else:
                self.mindate = min(self.mindate, datestr)
            if not self.maxdate:
                self.maxdate = datestr
            else:
                self.maxdate = max(self.maxdate, datestr)
        self.num_xd += 1

        self.puzzles_meta.append(puzrow)

    def meta(self):
        return 'pubid num dates formats copyrights editors'.split()

    def row(self):
        return [
                self.pubid,
                html.mkhref(str(self.num_xd), self.pubid),
                "%s &mdash; %s" % (self.mindate, self.maxdate),
                html_select_options(self.formats),
                html_select_options(self.copyrights),
                html_select_options(self.editors),
               ]


def tally_to_cell(d):
    freq_sorted = sorted([(v, k) for k, v in list(d.items())], reverse=True)

    if not freq_sorted:
        return ""
    elif len(freq_sorted) == 1:
        return "<br>".join("%s [x%s]" % (k, v) for v, k in freq_sorted)
    else:
        return "<select><option>" + "</option><option>".join("%s [x%s]" % (k, v) for v, k in freq_sorted) + "</select>"


def publication_header():
    return "PubId NumCollected DatesCollected Formats Copyrights Editors".split()


def main():
    parser = args_parser("generate publishers index html pages and index")

    args = get_args(parser=parser)

    outf = open_output()
    all_pubs = {}  # [(pubid,year)] -> PublicationStats
    pubyear_rows = {}
    similar = metadb.xd_similar()
    puzzles = metadb.xd_puzzles()
    outf.write_html('pub/index.html', pubyear.pubyear_html(), title='The xd crossword puzzle corpus')

    utils.log("collating puzzles")
    for puzrow in puzzles.values():
            pubid = utils.parse_pubid(puzrow.xdid)
            year = xdfile.year_from_date(puzrow.Date)
            k = (pubid, year or 9999)
            if k not in all_pubs:
                all_pubs[k] = PublicationStats(pubid)

            pubyear_rows[pubid] = []

            all_pubs[k].add(puzrow)


    pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', 'Grid_1A_1D', 'ReusedCluePct', 'SimilarGrids' ]
    utils.log('generating index pages')
    
    # dict to generate pub page with calendars
    pub_grids = defaultdict(dict)
    
    for pair, pub in sorted(list(all_pubs.items())):
        c_grids = {}
        pubid, year = pair
        progress(pubid)
   
        reused_clues = 0
        reused_answers = 0
        total_clues = 0
        total_similar = []

        rows = []
        
        for r in pub.puzzles_meta:
            similar_text = ""
            reused_clue_pct = "n/a"

            rsim = similar.get(r.xdid)
            if rsim:
                similar_pct = float(rsim.similar_grid_pct)
                if similar_pct > 0:
                    matches = [x.split('=') for x in rsim.matches.split()]
                    for xdid, pct in matches:
                        similar_text += '(%s%%) %s [%s]<br/>' % (pct, puzzles[xdid].Author, xdid)
                    total_similar.append(similar_pct)
                else:
                    similar_text = "0"

                nclues = int(rsim.total_clues)

                reused_clues += int(rsim.reused_clues)
                reused_answers += int(rsim.reused_answers)
                total_clues += nclues

                if nclues:
                    reused_clue_pct = int(100*(float(rsim.reused_clues) / float(nclues)))
                else:
                    reused_clue_pct = ''

            # Highlight only grids sized > 400 cells
            c_grids[r.Date] = { 'class' : 'biggrid' } if num_cells(r.Size) >= 400 else { 'class' : 'ordgrid' }

            row_dict = {} # Map row and style
            if similar_text and similar_text != "0":
                # http://stackoverflow.com/questions/1418838/html-making-a-link-lead-to-the-anchor-centered-in-the-middle-of-the-page
                pubidtext = '<span class="anchor" id="%s">' % r.xdid 
                pubidtext += '</span>'
                pubidtext += html.mkhref(r.xdid, '/pub/' + r.xdid)
                c_grids[r.Date] = { 
                        'link' : '/pub/%s%s/index.html#' % (pubid, year) + r.xdid,
                        'class': 'pctfilled'
                        }
                row_dict['class'] = 'puzzlehl'
                row_dict['param'] = 'onclick="location.href=\'/pub/%s\'"' % r.xdid
            else:
                pubidtext = r.xdid
                row_dict['class'] = 'puzzle'
           
            row = [ 
                pubidtext,
                r.Date,
                r.Size,
                r.Title,
                r.Author,
                r.Editor,
                r.Copyright,
                r.A1_D1,
                reused_clue_pct,
                similar_text
              ]

            outf.write_row('pub/%s%s.tsv' % (pubid, year), " ".join(pubyear_header), row)
            row_dict['row'] = row
            rows.append(row_dict)
       
        pub_grids[pubid][year] = c_grids

        # Generate calendar 
        onepubyear_html = GridCalendar(c_grids).formatyear(year, 6) + "<br>"
        
        # Generate html table
        onepubyear_html += html.html_table(rows, pubyear_header, "puzzle", "puzzles")
        outf.write_html("pub/%s%s/index.html" % (pubid, year), onepubyear_html, title="%s %s" % (pubid, year))
      
        
        cluepct = ""
        wordpct = ""
        if total_clues:
            cluepct = "%d%%" % int(100.0*(total_clues-reused_clues)/total_clues)
            wordpct = "%.2f%%" % int(100.0*(total_clues-reused_answers)/total_clues)

        pubyear_rows[pubid].append([
            pubid,
            str(year),
            len(rows),
            "%.2f/%d" % (sum(total_similar)/100.0, len(total_similar)),
            wordpct,
            cluepct
            ])


    # Generate /pub/[publisher][year] page
    for pubid in pub_grids.keys():
        body = []
        for y in sorted(pub_grids[pubid], reverse=True):
            body.append(GridCalendar(pub_grids[pubid][y]).formatyear(y, 12, vertical=True) + mktag('br','break'))
        outf.write_html("pub/%s/index.html" % pubid, ''.join(body), title="%s" % pubid)
    

    progress()


if __name__ == "__main__":
    main()
