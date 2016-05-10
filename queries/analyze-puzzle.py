#!/usr/bin/env python3

from queries.similarity import find_similar_to, find_clue_variants, load_clues, load_answers
from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile.html import html_header, html_footer, th
from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR

style_css = """
.xdgrid {
    margin-left: 10%;
    display: table;
    border-bottom: 1px solid black;
    border-right: 1px solid black;
}

.xdrow {
    display: table-row;
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
select { width: 100%; }
"""

def grid_to_html(xd):
    "htmlify this puzzle's grid"
    grid_html = '<div class="xdgrid">'
    for r, row in enumerate(xd.grid):
        grid_html += '<div class="xdrow">'
        for c, cell in enumerate(row):
            if cell == BLOCK_CHAR:
                grid_html += '<div class="xdcell block">'
            else:
                grid_html += '<div class="xdcell">'
            grid_html += cell  # TODO: expand rebus
            #  include other mutations that would still be valid
            grid_html += '</div>'
        grid_html += '</div>'
    grid_html += '</div>'

    return grid_html


def main():
    args = get_args("annotate puzzle clues with earliest date used in the corpus")
    outf = open_output()

    for fn, contents in find_files(*args.inputs, ext=".xd"):
        mainxd = xdfile(contents.decode('utf-8'), fn)

        main_html = html_header.format(title="xd analysis of %s" % mainxd.xdid())

        headers_html = '<ul class="xdheaders">'
        for k, v in mainxd.iterheaders():
            headers_html += '<li class="%s">%s</li>' % (k, v)
        headers_html += '</ul>'

        log("finding similar puzzles")
        similar_html = ""
        for pct, xd1, xd2 in sorted(find_similar_to(mainxd, corpus()), key=lambda x: x[0], reverse=True):
            # dump miniature grids with highlights of similarities
            #   click through to full comparison
            #   title="%d shared words"
            similar_html += '<li><a href="/%s" title="%s">%s (%d%%)</a></li>' % (xd2.xdid(), xd2.xdid(), xd2.filename, pct)

        log("finding similar clues")
        clues_html = '<table class="clues">' + th('pos', 'original clue and other uses', 'answer', 'other clues for this answer', 'other answers for this clue')

        nstaleclues = 0
        ntotalclues = 0
        for pos, clue, answer in mainxd.clues:
            progress(answer)

            clues_html += '<tr><td class="pos">%s%s.</td>' % pos

            other_answers = set()
            other_uses = { }  # [pubid] -> set(ClueAnswer)

            # insert our own clue
            mainpubid = mainxd.publication_id()
            maindate = mainxd.date()

            for clueans in find_clue_variants(clue):
                if clueans.pubid == mainpubid and clueans.date == maindate:
                    continue

                if clueans.answer != answer:
                    other_answers.add(clueans)
                else:
                    if clueans.pubid in other_uses:
                        otherpubs = other_uses[clueans.pubid]
                    else:
                        otherpubs = set()  # set of ClueAnswer
                        other_uses[clueans.pubid] = otherpubs

                    otherpubs.add(clueans)

            clues_html += '<td class="other-uses">'
            if len(other_uses) > 0:
                clues_html += '<select>'
                for pubid, uses in other_uses.items():
                    earliest_use = sorted(uses, key=lambda x: x.date or "z")[0]
                    if pubid == mainpubid and earliest_use.date == maindate:
                        clues_html += '<option name="%s">%s</option>' % (pubid, earliest_use.clue)
                    else:
                        clues_html += '<option name="%s">[%s%s] %s</option>' % (pubid, pubid, earliest_use.date, earliest_use.clue)

                clues_html += '</select>'
                nstaleclues += 1
            else:
                clues_html += '%s' % clue  # likely self-referential clue
        
            clues_html += '</td>'
            ntotalclues += 1

            clues_html += '<td class="answer">%s</td>' % answer

            clues_html += '<td class="other-clues">'
            bclues = load_answers().get(answer, [])
            if bclues:
                uses = []
                for bc, nuses in bclues.items():
                    clue_usages = [ ca for ca in load_clues().get(bc, [])  if ca.answer != answer ]

                    if clue_usages:
                        uses.append((nuses, clue_usages))

                if uses:
                    clues_html += '<select>'

                    for n, cas in sorted(uses, key=lambda x: x[0], reverse=True):
                        clues_html += '<option>%s' % cas[0].clue
                        if n > 1:
                            clues_html += ' [x%d]' % n
                        clues_html += '</option>'

                    clues_html += '</select>'
            clues_html += '</td>'

            clues_html += '<td class="other-answers">'
            if other_answers:
                clues_html += '<select>'
                for ca in sorted(other_answers, key=lambda x: x.date or "z", reverse=True):
                    clues_html += '<option name="%s">[%s%s] %s</option>' % (ca.pubid, ca.pubid, ca.date, ca.answer)
                clues_html += '</select>'
#                clues_html += '[%d total uses]' % len(other_answers)

            clues_html += '</td>'

            clues_html += '</tr>'
            
        clues_html += '</table>'

        clues_html += '%s/%s stale clues' % (nstaleclues, ntotalclues)

            # include number of times this boiled clue has been used overall (fade common clues answers)
            #  fade answers

            # include an answer per publisher:
            #  if the publisher has used this boiled clue before, show its earliest use
            #  otherwise choose a random clue from that publisher
            #  show how many other possible clues there are

            #for pubid, dt, clue in find_duplicate_clues(clue, answer):
            #    puzzle_html += "<option>[%s%s] %s [%s]</option>" % (pubid, dt, clue, len(all_clues[answer]))

            # illustrate show distribution of answerstotal:
            #  % of answers that are unique


        main_html += headers_html
        main_html += grid_to_html(mainxd)
        main_html += '<ul>' + similar_html + '</ul>'
        main_html += '<ul>' + clues_html + '</ul>'
        main_html += html_footer

        outf.write_file("%s/style.css" % mainxd.xdid(), style_css)
        outf.write_file("%s/index.html" % mainxd.xdid(), main_html.encode("ascii", 'xmlcharrefreplace').decode("ascii"))
        outf.write_file("analyze.log", get_log())
#        outf.write_file("stats.tsv", stats_tsv)

main()
