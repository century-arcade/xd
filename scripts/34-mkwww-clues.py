#!/usr/bin/env python3

from queries.similarity import load_clues, unboil, boil
from xdfile.utils import args_parser, get_args, open_output, find_files, info, progress, warn
from xdfile.html import th, td, mkhref, html_select_options
from xdfile import clues
import xdfile


def answers_from(clueset):
    return [ ca.answer for ca in clueset ]

def maybe_multstr(n):
    return (n > 1) and ("[x%d]" % n) or ""

def mkwww_cluepage(bc):
    if bc not in boiled_clues:
        return ''

    bcs = boiled_clues[bc]

    clue_html = ''
    clue_html += '<div>Variants: ' + html_select_options([ ca.clue for ca in bcs ]) + '</div>'
    clue_html += '<hr/>'
    clue_html += '<div>Answers for this clue: ' + html_select_options([ ca.answer for ca in bcs ]) + '</div>'
    clue_html += '<hr/>'

# TODO: maybe add pubyear chart back in, using stats.tsv as source data (by day-of-week)
#    clue_html += pubyear.pubyear_html([ (ca.pubyear()[0], ca.pubyear()[1], 1) for ca in bcs ])

    return clue_html

def main():
    global boiled_clues
    p = args_parser(desc='create clue index')
    p.add_argument('-N', '--top-n', type=int, default=100,
                   help='generate per-clue pages for top N most-used and top N most-ambiguous clues (default: 100)')
    args = get_args(parser=p)
    outf = open_output()

    boiled_clues = load_clues()

    biggest_clues = "<li>%d total clues, which boil down to %d distinct clues" % (len(clues()), len(boiled_clues))

    bcs = [ (len(v), bc, answers_from(v)) for bc, v in boiled_clues.items() ]

    nreused = len([bc for n, bc, _ in bcs if n > 1])
    biggest_clues += "<li>%d (%d%%) of these clues are used in more than one puzzle" % (nreused, nreused*100/len(boiled_clues))

    cluepages_to_make = set()

    # add all boiled clues from all input .xd files
    for fn, contents in find_files(*args.inputs, ext='.xd'):
        xd = xdfile.xdfile(contents.decode('utf-8'), fn)
        if xd.is_redacted():
            continue
        for pos, mainclue, mainanswer in xd.iterclues():
            bc = boil(mainclue)
            if bc:  # boil() returns None for clues with cross-references like "5 across"
                cluepages_to_make.add(bc)


    # add top 100 most used boiled clues from corpus
    biggest_clues += '<h2>Most used clues</h2>'

    biggest_clues += '<table class="clues most-used-clues">'
    biggest_clues += th("clue", "# uses", "answers used with this clue")
    for n, bc, ans in sorted(bcs, reverse=True)[:args.top_n]:
        cluepages_to_make.add(bc)
        biggest_clues += td(mkhref(unboil(bc), bc), n, html_select_options(ans))

    biggest_clues += '</table>'

    most_ambig = "<h2>Most ambiguous clues</h2>"
    most_ambig += '(clues with the largest number of different answers)'
    most_ambig += '<table class="clues most-different-answers">'
    most_ambig += th("Clue", "answers")

    for n, bc, ans in sorted(bcs, reverse=True, key=lambda x: len(set(x[2])))[:args.top_n]:
        cluepages_to_make.add(bc)
        clue = mkhref(unboil(bc), bc)
        if 'quip' in bc or 'quote' in bc or 'theme' in bc or 'riddle' in bc:
            most_ambig += td(clue, html_select_options(ans), rowclass="theme")
        else:
            most_ambig += td(clue, html_select_options(ans))

    most_ambig += '</table>'

    info("writing %d per-clue HTML pages..." % len(cluepages_to_make))
    nwritten = 0
    for bc in cluepages_to_make:
        # boiled clue is used as a directory name; skip ones that would blow past
        # Windows MAX_PATH (260 chars) when combined with the wwwroot/pub/clue/.../index.html prefix
        if len(bc) > 200:
            warn("skipping clue page (boiled clue too long, %d chars): %s..." % (len(bc), bc[:60]))
            continue
        contents = mkwww_cluepage(bc)
        if contents:
            outpath = 'pub/clue/%s/index.html' % bc
            progress(outpath, every=10)
            outf.write_html(outpath, contents, title=bc)
            nwritten += 1
    progress()
    info("wrote %d per-clue pages, done" % nwritten)

    info("writing clue index page...")
    outf.write_html('pub/clue/index.html', biggest_clues + most_ambig, title="Clues")
    info("clue index page, done")


main()
