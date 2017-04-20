#!/usr/bin/env python3
#
# Usage: $0 -c <corpus> -o wwwroot [<xdid>]
#
# Generate /pub/deep/<xdid> from given xdids or all similarpct > 25 in similar.tsv if if not given.
# <xdid> may be full pathnames; the base xdid will be parsed out.

from queries.similarity import grid_similarity, find_clue_variants, load_answers, load_clues, boil
import difflib
import datetime
from xdfile import utils
from xdfile.html import mktag, mkhref, html_select_options, html_select_options_freq, grid_to_html
import cgi

from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname, info, datestr_to_datetime
from xdfile import BLOCK_CHAR, ClueAnswer
from xdfile import metadatabase as metadb
import xdfile
import operator


def esc(s):
    return cgi.escape(s)


def html_prev_uses(pub_uses, mainxd, mainclue):
    sortable_uses = []
    mainxdid = mainxd.xdid()
    if pub_uses:
        for pubid, uses in pub_uses.items():
            # show the earliest unboiled clue
            for u in sorted(uses, key=lambda x: x.date or ""):
                # only show those published earlier
                if u.date and u.date <= mainxd.date():
                    if pubid == mainxdid and u.date == mainxd.date():
                        pass
                    else:
                        sortable_uses.append((u.date, u, 1))

    if sortable_uses:
        return html_select_options([ (clue, nuses) for dt, clue, nuses in sorted(sortable_uses, key=lambda x: x[0], reverse=True) ], force_top=mainclue)
    else:
        return ''


def html_other_clues(mainanswer, mainclue, mainxd):
    # bclues is all boiled clues for this particular answer: { [bc] -> #uses }
    bclues = load_answers().get(mainanswer, [])

    if bclues:
        uses = []
        for bc, nuses in bclues.items():
            # then find all clues besides this one
            clue_usages = []
            for ca in load_clues().get(bc, []):
                if ca.answer == mainanswer and ca.date < mainxd.date():
                    clue_usages.append(ca)

            if clue_usages:
                if nuses > 1:
                    # only use one (the most recent) ClueAnswer per boiled clue
                    # but use the clue only (no xdid)
                    ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1].clue
                else:
                    ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1]
                    uses.append((ca, nuses))

        if uses:
            return html_select_options_freq([(ca.clue, nuses) for ca, nuses in uses], force_top="[%s alternates]" % len(uses), add_total=False)

    return ''


def main():
    args = utils.get_args('generates .html diffs with deep clues for all puzzles in similar.tsv')
    outf = utils.open_output()

    similars = utils.parse_tsv('gxd/similar.tsv', 'Similar')
    xds_todo = [ xdfile.xdfile(open(fn).read(), fn) for fn in args.inputs ]
    if not xds_todo:
        # get list of all puzzles within last N days
        first_dt = datetime.date.today() - datetime.timedelta(days=30)
        xds_todo = [xd for xd in xdfile.corpus() if datestr_to_datetime(xd.date()) > first_dt]

    for mainxd in xds_todo:
        mainxdid = mainxd.xdid()
        progress(mainxdid)

        matches = metadb.xd_similar(mainxdid)

        xddates = {}
        xddates[mainxdid] = mainxd.date() # Dict to store XD dates for further sort
        html_grids = {}

        # these are added directly to similar.tsv
        nstaleclues = 0
        nstaleanswers = 0
        ntotalclues = 0

        dcl_html = '<tr>'
        dcl_html += '<th></th>'
        dcl_html += '<th>Clue</th>'
        dcl_html += '<th>ANSWERs</th>'
        dcl_html += '<th>Alt. clue possibilities</th>'
        dcl_html += '</tr>'

        deepcl_html = [] # keep deep clues to parse later - per row
        for pos, mainclue, mainanswer in mainxd.iterclues():
            if not pos:
                continue

            poss_answers = [] # TODO:
            pub_uses = {}  # [pubid] -> set(ClueAnswer)

            deepcl_html = [] # Temporary to be replaced late
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
            deepcl_html.append('<td class="other-uses">')

            prev_uses = html_prev_uses(pub_uses, mainxd, mainclue)
            if prev_uses:
                deepcl_html.append('<a href="/pub/clue/%s">%s [x%d]</a>' % (boil(mainclue), mainclue, len(prev_uses)))
                nstaleclues += 1
            else:
                deepcl_html.append(mainclue)

            deepcl_html.append('</td>')

            # add 'other answers' to clues_html
            deepcl_html.append('<td class="other-answers">')
            deepcl_html.append(html_select_options(poss_answers, strmaker=lambda ca: ca.answer, force_top=mainca, add_total=False))
            deepcl_html.append('</td>')

            # add 'other clues' to clues_html
            deepcl_html.append('<td class="other-clues">')

            other_clues = html_other_clues(mainanswer, mainclue, mainxd)
            if other_clues:
                deepcl_html.append(other_clues)
                nstaleanswers += 1

            deepcl_html.append('</td>')  # end 'other-clues'

            ntotalclues += 1
            # Quick and dirty - to be replaced
            dcl_html += '<tr>' + ' '.join(deepcl_html) + '</tr>'

        # Process deepclues
        diff_h = '<div class="main-container">'
        diff_h += grid_to_html(mainxd)
        diff_h += mktag('table', 'deepclues') + dcl_html + mktag('/table')
        diff_h += '</div>'

        info('writing deepclues for %s' % mainxdid)
        outf.write_html('pub/deep/%s/index.html' % mainxdid, diff_h,
                    title='Deep clue analysis for ' + mainxdid)


if __name__ == '__main__':
    main()
