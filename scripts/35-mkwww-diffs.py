#!/usr/bin/env python3
#
#

from queries.similarity import grid_similarity
import difflib
import datetime
from xdfile import utils
from xdfile.html import mktag, mkhref

from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
#from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
from xdfile import BLOCK_CHAR
from xdfile import metadatabase as metadb
import xdfile
import operator

def headers_to_html(xd):
    # headers
    r = '<div class="xdheaders"><ul class="xdheaders">'
    for k in "Title Author Editor Copyright".split():
        v = xd.get_header(k)
        if v:
            r += '<li class="%s">%s: <b>%s</b></li>' % (k, k, v)
        else:
            r += '<li></li>'
    r += '</ul></div>'
    return r


def grid_to_html(xd, compare_with=None):
    "htmlify this puzzle's grid"

    grid_html = '<div class="xdgrid">'
    for r, row in enumerate(xd.grid):
        grid_html += '<div class="xdrow">'
        for c, cell in enumerate(row):
            classes = [ "xdcell" ]

            if cell == BLOCK_CHAR:
                classes.append("block")

            if compare_with:
                if cell == compare_with.cell(r, c):
                    classes.append("match")
                else:
                    classes.append("diff")

            grid_html += '<div class="%s">' % " ".join(classes)
            grid_html += cell  # TODO: expand rebus
            #  include other mutations that would still be valid
            grid_html += '</div>' # xdcell
        grid_html += '</div>' #  xdrow
    grid_html += '</div>' # xdgrid

    return grid_html


def grid_diff_html(xd, compare_with=None):
    if compare_with:
        r = mktag('div', tagclass='fullgrid')
    else:
        r = mktag('div', tagclass='fullgrid main')

    similarity_pct = ''
    if compare_with:
        real_pct = grid_similarity(xd, compare_with)
        if real_pct < 25:
            return ''

        similarity_pct = " (%d%%)" % real_pct

    xdlink = mktag('div', tagclass='xdid', inner=mkhref("%s %s" % (xd.xdid(), similarity_pct), '/pub/' + xd.xdid()))
    if compare_with is not None:
        r += xdlink
    else:
        r += mktag('b', inner=xdlink)
    r += headers_to_html(xd)
    r += grid_to_html(xd, compare_with)

    r += '</div>' # solution
    return r


def main():
    args = utils.get_args('generates .html diffs for all puzzles in similar.tsv')
    outf = utils.open_output()

    similars = utils.parse_tsv('gxd/similar.tsv', 'Similar')
    xdids_todo = args.inputs or [ xdid for xdid, matches in metadb.get_similar_grids().items() if matches ]
    for mainxdid in xdids_todo:
        progress(mainxdid)

        mainxd = xdfile.get_xd(mainxdid)
        if not mainxd:
            continue

        matches = metadb.get_similar_grids().get(mainxdid, [])

        xddates = {}
        xddates[mainxdid] = mainxd.date() # Dict to store XD dates for further sort
        html_grids = {}
        html_clues = {}
        # Store in list to make further formatting as html table easier
        html_grids[mainxdid] = grid_diff_html(xdfile.get_xd(mainxdid))

        # Add for main XD
        diff_l = []
        for pos, mainclue, mainanswer in mainxd.iterclues():
            diff_h = mktag('div','fullgrid main') + '%s.&nbsp;' %pos
            diff_h += mainclue
            diff_h += mktag('span', tagclass='main', inner='&nbsp;~&nbsp;' + mainanswer.upper())
            diff_l.append(diff_h)
        html_clues[mainxdid] = diff_l
        # Process for all matches
        for xdid in matches:
            xd = xdfile.get_xd(xdid)
            # Continue if can't load xdid
            if not xd:
                continue
            xddates[xdid] = xd.date()
            # output each grid
            html_grids[xdid] = grid_diff_html(xd, compare_with=mainxd)
            diff_l = []
            # output comparison of each set of clues
            for pos, clue, answer in xd.iterclues():
                diff_h = mktag('div','fullgrid') + '%s.&nbsp;' %pos
                # Sometimes can return clue == None
                mainclue = mainxd.get_clue_for_answer(answer)
                sm = difflib.SequenceMatcher(lambda x: x == ' ', mainclue or '', clue)
                debug('MCLUE: %s [%s]' % (mainclue, sm.ratio()))
                if mainclue is None or sm.ratio() < 0.40:
                    diff_h += clue
                else:
                    # Compare based on op codes
                    for opcode in sm.get_opcodes():
                        c, a1, a2, b1, b2 = opcode
                        if c == 'equal':
                            diff_h += '<span class="match">%s</span>' % clue[b1:b2]
                        else:
                            diff_h += '<span class="diff">%s</span>' % clue[b1:b2]

                tagclass = 'match' if mainclue or answer == mainxd.get_answer(pos) else 'diff'
                diff_h += mktag('span', tagclass=tagclass, inner='&nbsp;~&nbsp;' + answer.upper())
                diff_h += mktag('/div')
                diff_l.append(diff_h)
            html_clues[xdid] = diff_l

        # Wrap into table
        diff_h = mktag('table') + mktag('tr')
        # Sort by date
        sortedkeys = sorted(xddates.items(), key=operator.itemgetter(1))
        for w, dt in sortedkeys:
            # Wrap into table
            diff_h += mktag('td') + html_grids[w] + mktag('/td')
        diff_h += mktag('/tr')
        for i, clue in enumerate(html_clues[sortedkeys[0][0]]):
            diff_h += mktag('tr')
            for w, dt in sortedkeys:
                if i < len(html_clues[w]):
                    diff_h += mktag('td') + html_clues[w][i] + mktag('/td')
            diff_h += mktag('/tr')
        diff_h += mktag('/table')
        outf.write_html('pub/%s/index.html' % mainxdid, diff_h, title='Comparison for ' + mainxdid)



if __name__ == '__main__':
    main()
