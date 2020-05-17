#!/usr/bin/env python

import os
import zipfile
import itertools

import xdfile

EOL = '\n'


def get_blank_grid(xd):
    emptygrid = ""
    for row in xd.grid:
        for c in row:
            if c == xdfile.BLOCK_CHAR:
                emptygrid += xdfile.BLOCK_CHAR
            else:
                emptygrid += "."
        emptygrid += EOL

    return emptygrid


def find_grid(fn):
    needle = get_blank_grid(xdfile(open(fn).read()))

    return [xd for xd in xdfile.corpus() if needle == get_blank_grid(xd)]


def get_all_words():
    ret = {}  # ["ANSWER"] = number of uses
    for xd in xdfile.corpus():
        for pos, clue, answer in xd.clues:
            ret[answer] = ret.get(answer, 0) + 1

    return ret


def most_used_grids(n=1):

    all_grids = {}
    for xd in xdfile.corpus():
        empty = get_blank_grid(xd)

        if empty not in all_grids:
            all_grids[empty] = []

        all_grids[empty].append(xd.filename)

    print("%s distinct grids" % len(all_grids))

    most_used = sorted(all_grids.items(), key=lambda x: -len(x[1]))

    for k, v in most_used[0:n]:
        print("used %s times" % len(v))
        gridlines = k.splitlines()
        for g, u in itertools.izip_longest(gridlines, sorted(v)):
            print("%15s    %s" % (u or "", g or ""))
        print()


def get_duplicate_puzzles():
    dupgrids = {}
    grids = {}
    for xd in xdfile.corpus():
        g = EOL.join(xd.grid)
        if g not in grids:
            grids[g] = [xd]
        else:
            grids[g].append(xd)
            dupgrids[g] = grids[g]

    return dupgrids.values()


if __name__ == "__main__":
    # import sys

    all_words = get_all_words()
    print("%d unique words.  most used words:" % len(all_words))
    for word, num_uses in sorted(all_words.items(), key=lambda x: -x[1])[0:10]:
        print (num_uses, word)

    print
    groups = {"small": 0, "medium":0, "large":0, "huge":0}
    for xd in xdfile.corpus():
        if xd.width() < 14 and xd.height() < 14:
            groups["small"] += 1
        elif xd.height() < 17 and xd.height() < 17:
            groups["medium"] += 1
        elif xd.height() < 25 and xd.height() < 25:
            groups["large"] += 1
        else:
            print (xd)
            groups["huge"] += 1

    for k, v in groups.items():
        print("%s %s" % (k,v))

    print

