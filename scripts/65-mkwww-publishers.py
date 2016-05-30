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
                mkhref(str(self.num_xd), self.pubid),
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

    # collate puzzles
    for tsvfn, contents in utils.find_files(*args.inputs, ext=".tsv"):
        for puzrow in utils.parse_tsv(tsvfn, "PuzzleRow").values():
            pubid = utils.parse_pubid_from_filename(puzrow.xdid)
            year = xdfile.year_from_date(puzrow.Date)
            k = (pubid, year or "0000")
            if k not in all_pubs:
                all_pubs[k] = PublicationStats(pubid)

            pubyear_rows[pubid] = []

            all_pubs[k].add(puzrow)


    pubyear_header = [ 'xdid', 'Date', 'Size', 'Title', 'Author', 'Editor', 'Copyright', '1Across_1Down', 'SimilarGrids', 'ReusedClues', 'ReusedAnswers' ]

    for pair, pub in list(all_pubs.items()):
        pubid, year = pair
        progress(pubid)
   
        rows = []
        for r in pub.puzzles_meta:
            row = [ r.xdid,
                r.Date,
                r.Size,
                r.Title,
                r.Author,
                r.Editor,
                r.Copyright,
                r.A1_D1,
#                similargrids,
#                int(r.reused_clues) or "",
#                int(r.reused_answers) or "",
              ]

            outf.write_row('pub/%s%s.tsv' % (pubid, year), " ".join(pubyear_header), row)
            rows.append(row)

        onepubyear_html = html.html_table(sorted(rows), pubyear_header, "puzzle")
        outf.write_html("pub/%s%s/index.html" % (pubid, year), onepubyear_html, title="%s %s" % (pubid, year))

        pubyear_rows[pubid].append([
            pubid,
            str(year),
            len(rows),
#            sum(similar),
#            avg(reused_clues),
#            avg(reused_answers),
            ])

    pub_header = "pubid year num_puzzles".split()            

    for pubid, rows in list(pubyear_rows.items()):
        pub_h = html.html_table(sorted(rows), pub_header, "onepub")
        outf.write_html("pub/%s/index.html" % pubid, pub_h, title="%s" % pubid)

    progress()


if __name__ == "__main__":
    main()
