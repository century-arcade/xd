#!/usr/bin/env python3

from xdfile.utils import get_args, open_output, find_files, log, debug, get_log, COLUMN_SEPARATOR, EOL, parse_tsv, progress, parse_pathname
from xdfile import corpus, xdfile, BLOCK_CHAR

import string
import random

# boil a clue down to its letters and numbers only
def boil(s):
    if "Across" in s or "Down" in s:  # skip self-referential clues
        return ""

    simple = string.ascii_letters + string.digits
    return "".join(c for c in s if c in simple).lower()


def load_clues():
    answers = {} # { ["ANSWER"] = { ["simplified clue text"] = set(fullclues) }
    for r in parse_tsv("clues.tsv", "AnswerClue"):
        try:
            pubid, dt, answer, clue = r
        except Exception as e:
            print(str(e), r)
            continue

        progress(dt or str(r), every=100000)

        if not clue:
            continue

        boiled_clue = boil(clue)
        if not boiled_clue:
            continue

        clue = "[%s %s] %s" % (dt, pubid, clue)

        if answer not in answers:
            clues = {}
            answers[answer] = clues
        else:
            clues = answers[answer]

        if boiled_clue not in clues:
            clues[boiled_clue] = set()

        clues[boiled_clue].add(r)

    progress()
    return answers


def reclue(xd, clueset):
    xd.clues = []
    nmissing = 0
    for posdir, posnum, answer in xd.iteranswers():
        if answer not in clueset:
            nmissing += 1
        else:
            clue = random_clue(clueset[answer])
            xd.clues.append(((posdir, posnum), clue, answer))

    xd.clues = sorted(xd.clues)

    return nmissing


def main():
    args = get_args("annotate puzzle clues with earliest date used in the corpus")
    outf = open_output()

    all_clues = load_clues()

    for fn, contents in find_files(*args.inputs, ext=".xd"):
        xd = xdfile(contents.decode('utf-8'), fn)
        if not xd.grid:
            continue

        try:
            new_clues = []
            npriorclues = 0
            for pos, clue, answer in xd.clues:
                bc = boil(clue)
                if bc and (answer in all_clues) and (bc in all_clues[answer]):
                    for pubid, dt, answer, clue in sorted(all_clues[answer][bc], key=1):  # oldest first
                        if pubid == xd.publication_id() and dt == xd.date():
                            # same clue as from this puzzle
                            continue
                        puzzle_html += "<option>[%s%s] %s [%s]</option>" % (pubid, dt, clue, len(all_clues[answer]))
                        npriorclues += 1

                new_clues.append((pos, clue, answer))

            puzzle_html += "%d%% recycled clues (%s/%s)" % (npriorclues*100/len(xd.clues), npriorclues, len(xd.clues)))

            outfn = "%s/index.html" % xd.xdid()

            outf.write_file(outfn, xd.to_unicode())
            outf.write_file(parse_pathname(fn).base + ".xd", contents)
        except Exception as e:
            log("error %s" % str(e))
            if args.debug:
                raise

    # write tsv rows for this batch
    outf.write_file("annotate.log", get_log())

main()
