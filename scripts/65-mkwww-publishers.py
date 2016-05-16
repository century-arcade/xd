#!/usr/bin/env python3

import re

from xdfile.metadatabase import xd_publications_meta, xd_puzzles_header, xd_puzzles_row, Publication
from xdfile.utils import find_files, parse_tsv_data, progress, open_output, get_args, args_parser, COLUMN_SEPARATOR
from xdfile.html import html_header, html_footer
import xdfile

style_css = """
.ReceiptId, .PublisherAbbr, .PublicationAbbr, .Date {
    display: none;
}
table {
/*	font-family: "Lucida Sans Unicode", "Lucida Grande", Sans-Serif; */
	font-size: 14px;
	background: #fff;
	margin: 25px;
/*	width: 480px; */
	border-collapse: collapse;
	text-align: left;
}
th {
	font-size: 16px;
	font-weight: normal;
	color: #039;
	padding: 10px 8px;
	border-bottom: 2px solid #6678b1;
}
option, select {
	border-bottom: 1px solid #ccc;
	color: #669;
    width: 100%;
	padding: 2px 2px;
}
td {
	border-bottom: 1px solid #ccc;
	color: #669;
	padding: 6px 8px;
}
tbody tr:hover td {
	background: #ccf;
}
"""

def mkhref(text, link, title=""):
    return '<a href="%s" title="%s">%s</a>' % (link, title, text)




def tally_to_dict(d, v):
    v = v.strip()
    if v:
        d[v] = d.get(v, 0) + 1



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
#    parser.add_argument('-m', '--min', action='store_const', help="minimum number of puzzles for publication to be included")
            #, dest="pub_min", default=1, 
    args = get_args(parser=parser)

    outf = open_output()

    all_pubs = {}  # [pubid] -> Publication

    total_xd = 0
    for xsv, contents in find_files(*args.inputs):
        for puzrow in parse_tsv_data(contents.decode('utf-8'), "Puzzle"):
            pubid = puzrow.PublicationAbbr
            if pubid not in all_pubs:
                all_pubs[pubid] = Publication(pubid)

            all_pubs[pubid].add(puzrow)
            total_xd += 1

    pubrows = [pub.row() for pubid, pub in sorted(all_pubs.items()) if pub.num_xd >= 1]

    pub_index = html_header.format(title="Index of crossword publications")
    pub_index += "<div>[The dropdown boxes are only used for compact display.]</div>"
    pub_index += html_table(pubrows, publication_header(), "Publication")
    pub_index += "<p>%d crosswords from %d publications</p>" % (total_xd, len(all_pubs))
    pub_index += html_footer

    for pubid, pub in list(all_pubs.items()):
        progress(pubid)
        onepub_html = html_header.format(title="Metadata for '%s' puzzles" % pubid)
        onepub_html += table_to_html(sorted(pub.puzzles_meta), xd_puzzles_header.split(COLUMN_SEPARATOR), "puzzle")
        onepub_html += html_footer
        outf.write_file("pubs/%s/index.html" % pubid, onepub_html)
        outf.write_file("pubs/%s/style.css" % pubid, style_css)

    progress("index")

    outf.write_file("pubs/index.html", pub_index.encode('ascii', 'xmlcharrefreplace'))
    outf.write_file("pubs/style.css", style_css)

    progress()


if __name__ == "__main__":
    main()
