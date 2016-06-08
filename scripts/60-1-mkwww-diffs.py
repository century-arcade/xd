#!/usr/bin/env python3

# Usage:
#   $0 [-c corpus] -o output_dir
#
# Generate HTML files based on similar.tsv
#

from queries.similarity import find_similar_to, find_clue_variants, load_clues, load_answers, grid_similarity
from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile.html import th, html_select_options, mktag
from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
import time
import cgi
from xdfile import utils, metadatabase


def xd_to_html(xd, compare_with=None):
    """
    Generates HTML code per each XD provided
    """
    r = mktag('div','fullgrid')
    similarity_pct = ''
    if compare_with:
        real_pct = grid_similarity(xd, compare_with)
        if real_pct < 25:
            return ''
        similarity_pct = " (%d%%)" % real_pct

    r += mktag('div', 'xdid')
    r += mkhref(xd.xdid() +' ' + similarity_pct, '/pub/' + xd.xdid())
    r += headers_to_html(xd)
    r += grid_to_html(xd, compare_with)
    r += mktag('/div') # solution
    return r


def headers_to_html(xd):
    """
    Generate headers for WHAT???
    """
    r = mktag('div', 'xdheaders') + mktag('ul', 'xdheaders')
    for k in ['Title', 'Author', 'Editor', 'Copyright']:
        v = xd.get_header(k)
        if v:
            r += mktag('li', k) + k + ': '
            r += mktag('b') + v + mktag('/b') + mktag('/li')
        else:
            r += mktag('li') + mktag('/li')
    r += mktag('/ul') + mktag('/div')
    return r


def grid_to_html(xd, compare_with=None):
    """
    htmlify this puzzle's grid
    """
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
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', default=False, help='analyze all puzzles, even those already in similar.tsv')
    args = get_args(parser=p)

    outf = open_output()

    prev_similar = parse_tsv('gxd/similar.tsv', "similar")
    #print(prev_similar)
    #quit()
    for fn, contents in find_files(*args.inputs, ext=".xd"):
        mainxd = xdfile(contents.decode('utf-8'), fn)

        if mainxd.xdid() in prev_similar:
            continue

        # find similar grids (pct, xd) for the mainxd in the corpus.  takes about 1 second per xd.  sorted by pct.

        similar_grids = sorted(find_similar_to(mainxd, corpus(), min_pct=0.20), key=lambda x: x[0], reverse=True)

        if similar_grids:
            log("similar: " + " ".join(("%s:%s" % (xd2.xdid(), pct)) for pct, xd1, xd2 in similar_grids))

        # clues_html is the 'deepclues' table
        clues_html = mktag('table', 'clues')
        clues_html += th('grid', 'original clue and previous uses', 'answers for this clue', 'other clues for this answer')

        mainpubid = mainxd.publication_id()
        maindate = mainxd.date()
        # go over each clue/answer, find all other uses, other answers, other possibilities.
        # these are added directly to similar.tsv
        nstaleclues = 0
        nstaleanswers = 0
        ntotalclues = 0

        for pos, mainclue, mainanswer in mainxd.iterclues():
            progress(mainanswer)

            poss_answers = []
            pub_uses = { }  # [pubid] -> set(ClueAnswer)

            mainca = ClueAnswer(mainpubid, maindate, mainanswer, mainclue)

            # 'grid position' column
            clues_html += mktag('tr') + mktag('td','pos') + pos +mktag('/td')

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
            clues_html += mktag('td', 'other-uses')
            if len(pub_uses) > 0:
                sortable_uses = []
                for pubid, uses in pub_uses.items():
                    # show the earliest unboiled clue
                    for u in sorted(uses, key=lambda x: x.date or ""):
                        # only show those published earlier
                        if u.date and u.date <= maindate:
                            if pubid == mainpubid and u.date == maindate:
                                pass
                            else:
                                stale = True
                                sortable_uses.append((u.date, u, 1))

                clues_html += html_select([ (clue, nuses) for dt, clue, nuses in sorted(sortable_uses, key=lambda x: x[0], reverse=True) ], top_option=mainclue)

            else:
                clues_html += mktag('div', 'original') + esc(mainclue) + mktag('/div')

            clues_html += mktag('/td')

            # add 'other answers' to clues_html
            clues_html += mktag('td',  'other-answers')
            clues_html += html_select_options(poss_answers,
                                strmaker=lambda ca: ca.answer, force_top=mainca)
            clues_html += mktag('/td')

            # add 'other clues' to clues_html
            clues_html += mktag('td', 'other-clues')

            # bclues is all boiled clues for this particular answer: { [bc] -> #uses }
            bclues = load_answers().get(mainanswer, [])
            stale_answer = False

            if bclues:
                uses = []
                for bc, nuses in bclues.items():
                    # then find all clues besides this one
                    clue_usages = [ ca for ca in load_clues().get(bc, []) if ca.answer == mainanswer and ca.date < maindate ]

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
                    clues_html += html_select(uses)

            clues_html += mktag('/td')  # end 'other-clues'
            clues_html += mktag('/tr')

            if stale_answer:
                nstaleanswers += 1
            if stale:
                nstaleclues += 1
            ntotalclues += 1

        clues_html += mktag('/table')

        # final output
        # dump miniature grids with highlights of similarities
        # main_html is /pub/{xdid}
        main_html = mktag('table') + mktag('tr')
        main_html += mktag('div', 'grids')

        # TODO: emit entire list sorted on .date().  The 'main' grid should be indicated with a different class.
        main_html += mktag('td') + xd_to_html(mainxd) + mktag('/td')

        all_pct = 0

        for pct, xd1, xd2 in sorted(similar_grids, key=lambda x: x[2].date()):
            main_html += mktag('td')
            main_html += mktag('div', 'similar-grid') + xd_to_html(xd2, mainxd)
            main_html += mktag('/td') + mktag('/div')
            main_html += mktag('/tr') + mktag('/div')
            all_pct += pct

        main_html += mktag('/div')

        # add deepclue analysis
        main_html += mktag('div', 'clues') + mktag('h2')
        main_html += '%d%% reused clues (%s/%s)' % (nstaleclues*100.0/ntotalclues, nstaleclues, ntotalclues)
        main_html += mktag('/h2') + mktag('ul') + clues_html + mktag('/ul')
        main_html += mktag('/div')

        if args.all or similar_grids:
            outf.write_html("pub/%s/index.html" %  mainxd.xdid(),
                        main_html, title="xd analysis of %s" % mainxd.xdid())

        """
        # summary row to similar.tsv
        metadatabase.append_row('gxd/similar.tsv', 'xdid similar_grid_pct reused_clues reused_answers total_clues matches', [
            mainxd.xdid(),
            int(100*sum(pct/100.0 for pct, xd1, xd2 in similar_grids)),
            nstaleclues,
            nstaleanswers,
            ntotalclues,
            " ".join(("%s=%s" % (xd2.xdid(), pct)) for pct, xd1, xd2 in similar_grids)
            ])
        """

if __name__ == '__main__':
    main()
