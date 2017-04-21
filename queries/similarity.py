#!/usr/bin/env python3

# Usage:
#    $0 [-c <corpus>] [-o similar.txt] <input_xd>
#
#  Searches through the corpus for similar grids.


import sys
import string
import re
import random


from xdfile.utils import progress, get_args, find_files, open_output, COLUMN_SEPARATOR, EOL, debug
from xdfile import xdfile, corpus, clues


g_boiled_clues = { }  # ["boiled clue"] = list(ClueAnswer(dt, pubid, clue, answer))
g_answers = { }  # ["ANSWER"] = list("boiled clue")


# inverse of hamming distance
# optimized version
def fast_grid_similarity(a, b):
    if len(a.grid) != len(b.grid) or len(a.grid[0]) != len(b.grid[0]):
        return 0

    r = 0
    for row1, row2 in zip(a.grid, b.grid):
        for i in range(len(row1)):
            if row1[i] == row2[i]:
                r += 1

    return r


def grid_similarity(a, b):
    if len(a.grid) != len(b.grid) or len(a.grid[0]) != len(b.grid[0]):
        return 0

    r = 0
    tot = 0
    for row1, row2 in zip(a.grid, b.grid):
        for i in range(len(row1)):
            if row1[i] != '#':
                tot += 1
                if row1[i] == row2[i]:
                    r += 1

    astr = a.to_unicode()
    bstr = b.to_unicode()
    if astr == bstr:
        return 100

    # add in a little bit of just whole string comparison to catch grid dissimilarities
    #total_diffs = sum(map(str.__eq__, astr, bstr)) / float(max(len(astr), len(bstr)))

    return int(r * 100 / float(tot))


def find_similar_to(needle, haystack, min_pct=0.3):
    if not needle.grid:
        return

    nsquares = len(needle.grid) * len(needle.grid[0])
    min_similarity = min_pct * nsquares
    for xd in haystack:
        if xd.filename == needle.filename:
            continue
        try:
            similarity = fast_grid_similarity(needle, xd)
        except Exception as e:
            debug(str(e))
            similarity = 0

        if similarity >= min_similarity:
            if needle.xdid() != xd.xdid(): # skip if same puzzle
                # recompute with slower metric
                similarity = grid_similarity(needle, xd)
                if similarity >= 25:
                    yield similarity, needle, xd


SIMPLE_CHARS = string.ascii_letters + string.digits + '_'

# boil a clue down to its letters and numbers only
def boil(s):
    if re.search('\d+[ \-](across|down)', s, re.IGNORECASE):
        return None

    boiled = "".join(c for c in s if c in SIMPLE_CHARS).lower()
    boiled = re.sub('[_\-]+','_', boiled)

    if boiled == "noclue":
        return None

    return boiled

def unboil(bc):
    return random.choice(load_clues()[bc]).clue


def load_clues():
    if not g_boiled_clues:
        for ca in clues():
            boiled_clue = boil(ca.clue)
            if not boiled_clue:
                continue

            if boiled_clue not in g_boiled_clues:
                real_clues = []
                g_boiled_clues[boiled_clue] = real_clues
            else:
                real_clues = g_boiled_clues[boiled_clue]

            real_clues.append(ca)

    return g_boiled_clues


# bclues is all boiled clues for this particular answer: { [bc] -> #uses }
def load_answers():
    if not g_answers:
        for ca in clues():
            if ca.answer not in g_answers:
                ans = dict()
                g_answers[ca.answer] = ans
            else: 
                ans = g_answers[ca.answer]

            bc = boil(ca.clue)
            ans[bc] = ans.get(bc, 0) + 1

    return g_answers

def find_clue_variants(clue):
    if not g_boiled_clues:
        load_clues()

    bc = boil(clue)
    if bc:
        return g_boiled_clues.get(bc, [])
    else:
        return []


def find_answers_for_clue(clue):
    if not g_boiled_clues:
        load_clues()

    bc = boil(clue)
    if not bc:
        return [ ]

    return set(ca.answer for ca in g_boiled_clues.get(bc, []))
    

xd_similar_header = COLUMN_SEPARATOR.join(["needle", "match", "percent"]) + EOL


def xd_similar_row(xd1, xd2, pct):
    return COLUMN_SEPARATOR.join([str(xd1), str(xd2), str(int(pct*100))]) + EOL


def main():
    args = get_args(desc='find similar grids')
    g_corpus = [ x for x in corpus() ]

    outf = open_output()

    outf.write(xd_similar_header)

    for fn, contents in find_files(*args.inputs, strip_toplevel=False):
        needle = xdfile(contents.decode("utf-8"), fn)
        for pct, a, b in find_similar_to(needle, g_corpus):
            outf.write(xd_similar_row(a, b, pct))

if __name__ == "__main__":
    main()
