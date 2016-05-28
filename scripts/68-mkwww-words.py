#!/usr/bin/env python3

from queries.similarity import find_similar_to, find_clue_variants, load_clues, load_answers
from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile.html import th, td, mkhref, html_select_options, pubyear_table
from xdfile.metadatabase import xd_puzzles_meta
from xdfile import corpus, clues

from collections import Counter
import random


g_puzzles_md = {}

def xd_metadata_row(xdid):
    if not g_puzzles_md:
        for r in xd_puzzles_meta():
            g_puzzles_md[r.xdid] = r
    return g_puzzles_md[xdid]


def mkwww_wordpage(answer):
    uses = all_uses[answer]

    h = ''
    h += pubyear_table([ ca.pubyear() for ca in uses ])
    h += '<hr/>'
    h += '<div>Clued as: ' + html_select_options([ ca.clue for ca in uses ]) + '</div>'
    h += '<h2>%d uses</h2>' % len(uses)

    h += '<table>'
    for ca in sorted(uses, reverse=True, key=lambda ca: ca.date):
        try:
            md = xd_metadata_row(ca.xdid())
            h += td(md.xdid, ca.clue, md.Author, md.Copyright)
        except Exception as e:
            h += td(ca.xdid(), ca.clue, str(e))
    h += '</table>'

#    h += '<hr/>'
#    h += '<div>Mutations: ' 
#    h +='</div>'
    
    return h 


def main():
    global all_uses
    args = get_args('create word pages and index')
    outf = open_output()

    all_uses = {}

    for ca in clues():
        if ca.answer not in all_uses:
            all_uses[ca.answer] = []
        all_uses[ca.answer].append(ca)

    h = '<li>%d different words</li>' % len(all_uses)

    h += '<h2>Most used words</h2>'
    
    h += '<table class="clues most-used-words">'
    h += th("word", "# uses", "clues used with this answer")

    wordpages_to_make = set(args.inputs)

    for answer, uses in sorted(all_uses.items(), reverse=True, key=lambda x: len(x[1]))[:100]:
        wordpages_to_make.add(answer)
        h += td(mkhref(answer.upper(), answer.lower()),
                len(uses),
                html_select_options(uses, strmaker=lambda ca: ca.clue))

    h += '</table>'

    for word in wordpages_to_make:
        outf.write_html('word/%s/index.html' % word.lower(), mkwww_wordpage(word), title=word)

    outf.write_html('word/index.html', h, title="Words")
        
main()
