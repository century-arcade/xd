#!/usr/bin/env python3
#
#

import difflib
from xdfile import utils
from xdfile.html import mktag, grid_diff_html
from xdfile.utils import warn

from xdfile.utils import debug, progress, info
#from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
from xdfile import metadatabase as metadb
import xdfile
import operator


def main():
    utils.get_args('generates .html diffs for all puzzles in similar.tsv')
    outf = utils.open_output()

    xdids_todo = {}

    for row in metadb.xd_similar_all():
        if row.xdid not in xdids_todo:
            xdids_todo[row.xdid] = []

        xdids_todo[row.xdid].append(row)


    xds_todo = list(xdids_todo)
    info("generating diffs for %d puzzles..." % len(xds_todo))
    # ~20 info() lines spread evenly so CI logs stay readable for any list size
    info_every = max(1, len(xds_todo) // 20)
    for npuzzle, mainxdid in enumerate(xds_todo):
        progress(mainxdid)
        if npuzzle and npuzzle % info_every == 0:
            info("  ... %d/%d (%.0f%%) diffs generated" % (npuzzle, len(xds_todo), 100 * npuzzle / len(xds_todo)))

        mainxd = xdfile.get_xd(mainxdid)
        if not mainxd:
            warn('%s not in corpus' % mainxdid)
            continue

        if mainxd.is_redacted():
            continue  # answers are all 'X' — skip diff rendering

        matches = xdids_todo[mainxdid]
        debug('generating diffs for %s (%d matches)' % (mainxdid, len(matches)))

        xddates = {}
        xddates[mainxdid] = mainxd.date() # Dict to store XD dates for further sort
        html_grids = {}
        html_clues = {}
        # Store in list to make further formatting as html table easier
        html_grids[mainxdid] = grid_diff_html(xdfile.get_xd(mainxdid))

        # Add for main XD
        diff_l = []
        for pos, mainclue, mainanswer in mainxd.iterclues():
            if not mainclue:
                continue
            diff_h = mktag('div','fullgrid main') + '%s.&nbsp;' %pos
            diff_h += mainclue
            diff_h += mktag('span', tagclass='main', inner='&nbsp;~&nbsp;' + mainanswer.upper())
            diff_l.append(diff_h)
        html_clues[mainxdid] = diff_l

        # Process for all matches
        for row in matches:
            xdid = row.match_xdid
            xd = xdfile.get_xd(xdid)
            # Continue if can't load xdid
            if not xd:
                continue
            if xd.is_redacted():
                continue  # answers are all 'X' — skip from diff comparison
            xddates[xdid] = xd.date()
            # output each grid
            html_grids[xdid] = grid_diff_html(xd, compare_with=mainxd)
            diff_l = []
            # output comparison of each set of clues
            for pos, clue, answer in xd.iterclues():
                diff_h = mktag('div','fullgrid') + '%s.&nbsp;' %pos
                if not clue:
                    continue
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
    progress()
    info("generated %d diffs, done" % len(xds_todo))



if __name__ == '__main__':
    main()
