#!/usr/bin/env python3

from collections import Counter
import re

from xdfile.utils import progress, open_output, get_args, args_parser, COLUMN_SEPARATOR
from xdfile import html, utils, catalog
from xdfile import metadatabase as metadb
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

    similar = utils.parse_tsv('gxd/similar.tsv', 'Similar')  # [xdid] -> (similar_grid_pct, reused_clues, reused_answers, total_clues)

    # collate puzzles
    for tsvfn, contents in utils.find_files(*args.inputs, ext=".tsv"):
        for puzrow in utils.parse_tsv(tsvfn, "PuzzleRow").values():
            pubid = utils.parse_pubid(puzrow.xdid)
            year = xdfile.year_from_date(puzrow.Date)
            k = (pubid, year or "9999")
            if k not in all_pubs:
                all_pubs[k] = PublicationStats(pubid)

            pubyear_rows[pubid] = []

            all_pubs[k].add(puzrow)


    pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', 'Grid_1A_1D', 'SimilarGrids' ]

    for pair, pub in list(all_pubs.items()):
        pubid, year = pair
        progress(pubid)
   
        reused_clues = 0
        reused_answers = 0
        total_clues = 0
        total_similar = []

        rows = []
        for r in pub.puzzles_meta:
            rsim = similar.get(r.xdid)
            if rsim:
                similar_pct = float(rsim.similar_grid_pct)
                if similar_pct > 0:
                    total_similar.append(similar_pct)
                    similar_pct = "%.2f" % (similar_pct/100.0)
                else:
                    similar_pct = "0"

                reused_clues += int(rsim.reused_clues)
                reused_answers += int(rsim.reused_answers)
                total_clues += int(rsim.total_clues)
            else:
                similar_pct = ""

            if similar_pct and similar_pct != "0":
                pubidtext = html.mkhref(r.xdid, '/pub/' + r.xdid)
            else:
                pubidtext = r.xdid

            row = [ 
                pubidtext,
                r.Date,
                r.Size,
                r.Title,
                r.Author,
                r.Editor,
                r.Copyright,
                r.A1_D1,
                similar_pct,
              ]

            outf.write_row('pub/%s%s.tsv' % (pubid, year), " ".join(pubyear_header), row)
            rows.append(row)

        onepubyear_html = html.html_table(sorted(rows, key=lambda r: r[1]), pubyear_header, "puzzle")
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

    pub_header = "Year NumberOfPuzzles SimilarPuzzles OriginalWordPct OriginalCluePct".split()            

    for pubid, tsvrows in list(pubyear_rows.items()):
        rows = []
        for pubid, y, n, similarity, wordpct, cluepct in tsvrows:
            pubhref = html.mkhref(str(y), '/pub/%s%s' % (pubid, y))
            rows.append((pubhref, n, similarity, wordpct, cluepct))
        pub_h = html.html_table(sorted(rows), pub_header, "onepub")
        outf.write_html("pub/%s/index.html" % pubid, pub_h, title="%s" % pubid)

    progress()


if __name__ == "__main__":
    main()
