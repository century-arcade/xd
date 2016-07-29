#!/usr/bin/env python3
#
# Usage: $0 -c <corpus> -o wwwroot [<xdid>]
#
# Generate /pub/deep/<xdid> from given xdids or all similarpct > 25 in similar.tsv if if not given.
# <xdid> may be full pathnames; the base xdid will be parsed out.

from queries.similarity import grid_similarity, find_clue_variants, load_answers, load_clues
import difflib
import datetime
from xdfile import utils
from xdfile.html import mktag, mkhref, html_select_options
import cgi

from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile import BLOCK_CHAR, ClueAnswer
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


# pairs of ("option", num_uses)
def html_select(options, top_option=""):
    if not options:
        return str(top_option)

    r = '<div class="actuals">'

    r += '<select>'
    if top_option:
        r += '<option>%s</option>' % top_option

    for opt, n in sorted(options, key=lambda x: x[1], reverse=True):
        r += '<option>'

        s = esc(str(opt))
        
        if n > 1:
            r += '%s [x%d]' % (s, n)
        else:
            r += s

        r += '</option>'
    r += '</select></div>'
    r += '<div class="num"> %d</div>' % len(options)
    return r


def esc(s):
    return cgi.escape(s)


def main():
    args = utils.get_args('generates .html diffs with deep clues for all puzzles in similar.tsv')
    outf = utils.open_output()

    similars = utils.parse_tsv('gxd/similar.tsv', 'Similar')
    xdids_todo = [ parse_pathname(fn).base for fn in args.inputs ] 
    if not xdids_todo:
        xdids_todo = [ xdid for xdid, matches in metadb.get_similar_grids().items() if matches ]

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

        # these are added directly to similar.tsv
        nstaleclues = 0
        nstaleanswers = 0
        ntotalclues = 0

        poss_answers = [] # TODO: 
        pub_uses = {}  # [pubid] -> set(ClueAnswer)

        dcl_html = '' 
        deepcl_html = [] # keep deep clues to parse later - per row
        for pos, mainclue, mainanswer in mainxd.iterclues():
            deepcl_html = [] # Temporary to be replaced lately
            mainca = ClueAnswer(mainxdid, mainxd.date(), mainanswer, mainclue)

            # 'grid position' column
            deepcl_html.append('<td class="pos">%s.</td>' % pos)

            # find other uses of this clue, and other answers, in a single pass
            for clueans in find_clue_variants(mainclue):
                if clueans.answer != mainanswer:
                    poss_answers.append(clueans)

                if clueans.answer == mainanswer:
                    if clueans.pubid in pub_uses:
                        otherpubs = pub_uses[clueans.pubid]
                    else:
                        otherpubs = set()  # set of ClueAnswer
                        pub_uses[clueans.pubid] = otherpubs
                    otherpubs.add(clueans)

            # add 'other uses' to clues_html
            stale = False
            deepcl_html.append('<td class="other-uses">')

            if len(pub_uses) > 0:
                sortable_uses = []
                for pubid, uses in pub_uses.items():
                    # show the earliest unboiled clue
                    for u in sorted(uses, key=lambda x: x.date or ""):
                        # only show those published earlier
                        if u.date and u.date <= mainxd.date():
                            if pubid == mainxdid and u.date == mainxd.date():
                                pass
                            else:
                                stale = True
                                sortable_uses.append((u.date, u, 1))

                deepcl_html.append(html_select([ (clue, nuses) for dt, clue, nuses in sorted(sortable_uses, key=lambda x: x[0], reverse=True) ], top_option=mainclue))

            else:
                deepcl_html.append('<div class="original">%s</div>' % esc(mainclue))

            deepcl_html.append('</td>')

            # add 'other answers' to clues_html

            deepcl_html.append('<td class="other-answers">')
            deepcl_html.append(html_select_options(poss_answers, strmaker=lambda ca: ca.answer, force_top=mainca))
            deepcl_html.append('</td>')

            # add 'other clues' to clues_html
            deepcl_html.append('<td class="other-clues">')

            # bclues is all boiled clues for this particular answer: { [bc] -> #uses }
            bclues = load_answers().get(mainanswer, [])
            stale_answer = False

            if bclues:
                uses = []
                for bc, nuses in bclues.items():
                    # then find all clues besides this one
                    clue_usages = [ ca for ca in load_clues().get(bc, []) if ca.answer == mainanswer and ca.date < mainxd.date() ]

                    if clue_usages:
                        stale_answer = True
                        if nuses > 1:
                            # only use one (the most recent) ClueAnswer per boiled clue
                            # but use the clue only (no xdid)
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1].clue
                        else:
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1]
                            uses.append((ca, nuses))

                if uses:
                    deepcl_html.append(html_select(uses))

            deepcl_html.append('</td>')  # end 'other-clues'

            if stale_answer:
                nstaleanswers += 1
            if stale:
                nstaleclues += 1
            ntotalclues += 1
            # Quick and dirty - to be replaced
            dcl_html += '<tr>' + ' '.join(deepcl_html) + '</tr>'   

        # Store in list to make further formatting as html table easier
        mainxd = xdfile.get_xd(mainxdid)
        if mainxd:
            html_grids[mainxdid] = grid_diff_html(mainxd)

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
                sm = difflib.SequenceMatcher(lambda x: x == ' ', mainxd.get_clue(pos) or '', clue)
                if sm.ratio() < 0.50:
                    diff_h += clue
                else:
                    # Compare based on op codes
                    for opcode in sm.get_opcodes():
                        c, a1, a2, b1, b2 = opcode
                        if c == 'equal':
                            diff_h += '<span class="match">%s</span>' % clue[b1:b2]
                        else:
                            diff_h += '<span class="diff">%s</span>' % clue[b1:b2]
                    
                diff_h += mktag('span', tagclass=(answer == mainxd.get_answer(pos)) and 'match' or 'diff', inner='&nbsp;~&nbsp;' + answer.upper())
                diff_h += mktag('/div')
                diff_l.append(diff_h)
            html_clues[xdid] = diff_l 
        

        print('writing table')
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
        # Process deepclues
        diff_h += mktag('table') + dcl_html + mktag('/table') 

        diff_h += mktag('/table')
        
        outf.write_html('pub/deep/%s/index.html' % mainxdid, diff_h, 
                    title='Deep clue comparison for ' + mainxdid)


if __name__ == '__main__':
    main()
