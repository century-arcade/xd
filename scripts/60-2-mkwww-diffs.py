#!/usr/bin/env python3
#
#

from queries.similarity import grid_similarity
import difflib
import datetime
from xdfile import utils
from xdfile.html import mktag

from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
#from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
from xdfile import BLOCK_CHAR
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

            if compare_with and cell == compare_with.cell(r, c):
                classes.append("same")

            grid_html += '<div class="%s">' % " ".join(classes)
            grid_html += cell  # TODO: expand rebus
            #  include other mutations that would still be valid
            grid_html += '</div>' # xdcell
        grid_html += '</div>' #  xdrow
    grid_html += '</div>' # xdgrid

    return grid_html


def grid_diff_html(xd, compare_with=None):
    r = '<div class="fullgrid">'

    similarity_pct = ''
    if compare_with:
        real_pct = grid_similarity(xd, compare_with)
        if real_pct < 25:
            return ''

        similarity_pct = " (%d%%)" % real_pct

    r += '<div class="xdid"><a href="/pub/%s">%s %s</a></div>' % (xd.xdid(), xd.xdid(), similarity_pct)
    r += headers_to_html(xd)
    r += grid_to_html(xd, compare_with)

    r += '</div>' # solution
    return r


def main():
    args = utils.get_args('generates .html diffs for all puzzles in similar.tsv')
    outf = utils.open_output()

    corpus = dict((xd.xdid(), xd) for xd in xdfile.corpus())
    
    for mainxdid, simrow in utils.parse_tsv('gxd/similar.tsv', 'Similar').items():
        try:
            mainxd = corpus[mainxdid]
        except:
            utils.log('Xdid not found: %s' % mainxdid)
            continue

        xddates = {}
        xddates[mainxdid] = mainxd.date() # Dict to store XD dates for further sort
        matches = [ x.split('=') for x in simrow.matches.split() ]
        html_grids = {}
        html_clues = {}
        # TODO: sort grids by date
        # TODO: wrap grids into table
        
        # Store in list to make further formatting as html table easier
        html_grids[mainxdid] = grid_diff_html(corpus[mainxdid])

        # Add for main XD
        diff_l = []
        for pos, mainclue, answer in mainxd.iterclues():
            diff_h = mktag('div','fullgrid') + '%s.&nbsp;' %pos
            diff_h += mainclue
            diff_h += '&nbsp;' + answer.upper() + mktag('/div')
            diff_l.append(diff_h)
        html_clues[mainxdid] = diff_l
       
        # Process for all matches
        for xdid, pct in matches:
            xd = corpus[xdid]
            xddates[xdid] = xd.date()
            # output each grid
            html_grids[xdid] = grid_diff_html(xd, compare_with=mainxd)
           
            diff_l = []
            # output comparison of each set of clues
            for pos, mainclue, answer in mainxd.iterclues():
                diff_h = mktag('div','fullgrid') + '%s.&nbsp;' %pos 
                # Sometimes can return clue == None
                clue = xd.get_clue(pos) if xd.get_clue(pos) else ''
                sm = difflib.SequenceMatcher(lambda x: x == ' ', mainclue, clue)
                # Compare based on op codes
                for opcode in sm.get_opcodes():
                    c, a1, a2, b1, b2 = opcode
                    if c == 'equal':
                        diff_h += '<span class="match">%s</span>' % clue[b1:b2]
                    else:
                        diff_h += '<span class="diff">%s</span>' % clue[b1:b2]
                    
                diff_h += '&nbsp;' + answer.upper() + mktag('/div')
                diff_l.append(diff_h)
            html_clues[xdid] = diff_l 
        

        # Wrap into table
        diff_h = mktag('table') + mktag('tr')
        # Sort by date
        sortedkeys = sorted(xddates, key=operator.itemgetter(1)) 
        for w in sortedkeys:
            # Wrap into table
            diff_h += mktag('td') + html_grids[w] + mktag('/td')
        diff_h += mktag('/tr')
        
        for i, clue in enumerate(html_clues[sortedkeys[0]]):
            diff_h += mktag('tr')
            for w in sortedkeys:
                diff_h += mktag('td') + html_clues[w][i] + mktag('/td')
            diff_h += mktag('/tr') 
        diff_h += mktag('/table')
        
        outf.write_html('pub/%s/index.html' % mainxdid, diff_h, title='Comparison for ' + simrow.xdid)



if __name__ == '__main__':
    main()
