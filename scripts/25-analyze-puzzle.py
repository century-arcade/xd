#!/usr/bin/env python3

# Usage:
#   $0 [-c corpus] <input.xd>
#
# updates similar.tsv for later usage
#

from queries.similarity import find_similar_to, find_clue_variants, load_clues, load_answers, grid_similarity
from xdfile.utils import get_args, open_output, find_files, log, info, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile import xdfile, corpus, ClueAnswer, BLOCK_CHAR
import time
from xdfile import utils, metadatabase


def main():
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', default=False, help='analyze all puzzles, even those already in similar.tsv')
    args = get_args(parser=p)
    outf = open_output()

    prev_similar = parse_tsv('gxd/similar.tsv', "similar")
    for fn, contents in find_files(*args.inputs, ext=".xd"):
        progress(fn)
        mainxd = xdfile(contents.decode('utf-8'), fn)

        if mainxd.xdid() in prev_similar:
            continue  # skip reprocessing .xd that are already in similar.tsv

        """ find similar grids (pct, xd) for the mainxd in the corpus.
        Takes about 1 second per xd.  sorted by pct.
        """
        similar_grids = sorted(find_similar_to(mainxd, corpus(), min_pct=0.20),
                               key=lambda x: x[0], reverse=True)

        if similar_grids:
            info("similar: " + " ".join(("%s=%s" % (xd2.xdid(), pct))
                                       for pct, xd1, xd2 in similar_grids))

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

            # bclues is all boiled clues for this particular answer: { [bc] -> #uses }
            bclues = load_answers().get(mainanswer, [])
            stale_answer = False

            # What's this stands for???
            if bclues:
                uses = []
                for bc, nuses in bclues.items():
                    # then find all clues besides this one
                    clue_usages = [ ca for ca in load_clues().get(bc, [])
                                    if ca.answer == mainanswer and ca.date < maindate ]

                    if clue_usages:
                        stale_answer = True
                        if nuses > 1:
                            # only use one (the most recent) ClueAnswer per boiled clue
                            # but use the clue only (no xdid)
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1].clue
                        else:
                            ca = sorted(clue_usages, key=lambda ca: ca.date or "z")[-1]
                        uses.append((ca, nuses))
        # summary row to similar.tsv
        row_header = 'xdid similar_grid_pct reused_clues reused_answers total_clues matches'
        metadatabase.append_row('gxd/similar.tsv', row_header, [
            mainxd.xdid(),
            int(100*sum(pct/100.0 for pct, xd1, xd2 in similar_grids)),
            nstaleclues,
            nstaleanswers,
            ntotalclues,
            " ".join(("%s=%s" % (xd2.xdid(), pct)) for pct, xd1, xd2 in similar_grids)
            ])


if __name__ == '__main__':
    main()
