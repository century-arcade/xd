#!/usr/bin/env python3

from queries.similarity import find_similar_to, find_clue_variants, load_clues, load_answers, grid_similarity
from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile.html import html_header, html_footer, th
from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
import time
import cgi

style_css = """
.fullgrid {
    margin-left: 20px;
    margin-bottom: 20px;
}

.xdgrid {
    margin: auto;
    display: table;
    border-bottom: 1px solid black;
    border-right: 1px solid black;
}

.xdrow {
    display: table-row;
}

.xdcell.same {
    background: lightgreen;
}

.xdcell {
    display: table-cell;
    text-align: center;
    border-top: 1px solid black;
    border-left: 1px solid black;
    width: 8px;
    height: 8px;
    padding: 4px;
}

.xdcell.block {
    background: black;
}

.clues td {
    border-left: 1px solid grey;
    border-bottom: 1px solid grey;
    padding: 2px;
    padding-left: 6px;
}

.original {
    background:white;
}

.num { 
    width: 8%; 
    text-align: right;
    padding-right: 4px;
}
table div {
    float: left;
}

.grids .xdid {
    text-align: center;
}

.grids > div {
    float: left;
}

.clues {
    clear: both;
}
.actuals { width: 85%; }
select { width: 100%; }
.other-answers {
    text-align: center;
    }
"""

def grid_to_html(xd, compare_with=None):
    "htmlify this puzzle's grid"

    # headers

    grid_html = '<div class="fullgrid">'
    grid_html += '<div class="xdheaders"><ul class="xdheaders">'
    for k, v in xd.iterheaders():
        grid_html += '<li class="%s">%s: <b>%s</b></li>' % (k, k, v)
    grid_html += '</ul></div>'

    similarity_pct = ""
    if compare_with:
        similarity_pct = " (%d%%)" % grid_similarity(xd, compare_with)

    grid_html += '<div class="xdid"><a href="/%s" title="%s">%s %s</a></div>' % (xd.filename, "", xd.xdid(), similarity_pct)
    grid_html += '<div class="xdgrid">'
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
    grid_html += '</div>' # solution

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
    args = get_args("annotate puzzle clues with earliest date used in the corpus")
    outf = open_output()

    for fn, contents in find_files(*args.inputs, ext=".xd"):
        mainxd = xdfile(contents.decode('utf-8'), fn)

        similar_grids = sorted(find_similar_to(mainxd, corpus()), key=lambda x: x[0], reverse=True)

        log("finding similar clues")
        clues_html = '<table class="clues">' + th('grid', 'original clue and previous uses', 'answers for this clue', 'other clues for this answer')

        nstaleclues = 0
        ntotalclues = 0
        for pos, mainclue, mainanswer in mainxd.clues:
            progress(mainanswer)

            clues_html += '<tr><td class="pos">%s%s.</td>' % pos

            poss_answers =  { }
            pub_uses = { }  # [pubid] -> set(ClueAnswer)

            # insert our own clue
            mainpubid = mainxd.publication_id()
            maindate = mainxd.date()

            for clueans in find_clue_variants(mainclue):
                poss_answers[clueans.answer] = poss_answers.get(clueans.answer, 0) + 1

                if clueans.answer == mainanswer:
                    if clueans.pubid in pub_uses:
                        otherpubs = pub_uses[clueans.pubid]
                    else:
                        otherpubs = set()  # set of ClueAnswer
                        pub_uses[clueans.pubid] = otherpubs

                    otherpubs.add(clueans)

            stale = False
            clues_html += '<td class="other-uses">'
            if len(pub_uses) > 0:
                sortable_uses = []
                for pubid, uses in pub_uses.items():
                    # show the earlist unboiled clue
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
                clues_html += '<div class="original">%s</div>' % esc(mainclue)
        
            clues_html += '</td>'
            if stale:
                nstaleclues += 1
            ntotalclues += 1

            clues_html += '<td class="other-answers">'
            clues_html += html_select([ (k, n) for k, n in poss_answers.items() if k != mainanswer ], top_option=mainanswer)
            clues_html += '</td>'

            clues_html += '<td class="other-clues">'

            # bclues is all boiled clues for this particular answer: { [bc] -> #uses }
            bclues = load_answers().get(mainanswer, [])
            if bclues:
                uses = []
                for bc, nuses in bclues.items():
                    # then find all clues besides this one
                    clue_usages = [ ca for ca in load_clues().get(bc, []) if ca.answer == mainanswer and ca.date < maindate ]

                    if clue_usages:
                        if nuses > 1:
                            # only use one (the most recent) ClueAnswer per boiled clue
                            # but use the clue only (no xdid)
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1].clue
                        else:
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1]
                        uses.append((ca, nuses))
                if uses:
                    clues_html += html_select(uses)
            clues_html += '</td>'


            clues_html += '</tr>'
            
        clues_html += '</table>'


        main_html = html_header.format(title="xd analysis of %s" % mainxd.xdid())

        main_html += '<i>Generated on %s ' % time.strftime('%F')
        main_html += "from a corpus of %s puzzles.</i>" % len([ x for x in corpus() ])

        # similar grids
        main_html += '<div class="grids">'
        main_html += grid_to_html(mainxd)

        # dump miniature grids with highlights of similarities
        for pct, xd1, xd2 in similar_grids:
            main_html += '<div class="similar-grid">' + grid_to_html(xd2, mainxd)
            main_html += '</div>'
            main_html += '</div>'

        main_html += '</div>'


        # clue analysis
        main_html += '<div class="clues">'
        main_html += '<h2>%d%% reused clues (%s/%s)</h2>' % (nstaleclues*100.0/ntotalclues, nstaleclues, ntotalclues)
        main_html += '<ul>' + clues_html + '</ul>'
        main_html += html_footer

        main_html += '</div>'

        # summary.tsv row
        outf.append_tsv('summary.tsv', 'xdid stale_clues_pct similar_grids Title Author Editor',
                mainxd.xdid(), int(nstaleclues*100.0/ntotalclues), " ".join("(%d%%) %s" % (pct, xd2.xdid()) for pct, xd1, xd2 in similar_grids),
                mainxd.get_header("Title"), mainxd.get_header("Author"), mainxd.get_header("Editor"))

        outf.write_file("%s/style.css" % mainxd.xdid(), style_css)
        outf.write_file("%s/index.html" % mainxd.xdid(), main_html.encode("ascii", 'xmlcharrefreplace').decode("ascii"))
    outf.write_file("analyze.log", get_log())
#        outf.write_file("stats.tsv", stats_tsv)

main()
