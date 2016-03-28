#!/usr/bin/python

import sys
import itertools

import xdfile


# inverse of hamming distance
# optimized version
def fast_grid_similarity(a, b):
    if len(a.grid) != len(b.grid) or len(a.grid[0]) != len(b.grid[0]):
        return 0

    r = 0
    for row1, row2 in itertools.izip(a.grid, b.grid):
        for i in xrange(len(row1)):
            if row1[i] == row2[i]:
                r += 1

    return r


def grid_similarity(a, b):
    if len(a.grid) != len(b.grid) or len(a.grid[0]) != len(b.grid[0]):
        return 0

    r = 0
    tot = 0
    for row1, row2 in itertools.izip(a.grid, b.grid):
        for i in xrange(len(row1)):
            if row1[i] != '#':
                tot += 1
                if row1[i] == row2[i]:
                    r += 1

    astr = a.to_unicode()
    bstr = b.to_unicode()
    if astr == bstr:
        return 1

    # add in a little bit f
    total_diffs = sum(itertools.imap(unicode.__eq__, astr, bstr)) / float(max(len(astr), len(bstr)))

    return (r + total_diffs) / float(tot + 1)


def same_answers(a, b):
    ans1 = set(sol for pos, clue, sol in a.clues)
    ans2 = set(sol for pos, clue, sol in b.clues)
    return ans1 & ans2


def find_similar_to(needle, haystack, min_pct=0.3, num_answers=0):
    ret = []
    nsquares = len(needle.grid) * len(needle.grid[0])
    for xd in haystack:
        if xd.filename == needle.filename:
            continue
        try:
            pct = fast_grid_similarity(needle, xd) / float(nsquares)
        except Exception:
            pct = 0

        if pct >= min_pct:
            s = same_answers(needle, xd)
            if not num_answers or len(s) >= num_answers:
                ret.append((pct, needle, xd, s))
    return ret


def main():
    corpus = xdfile.load_corpus(sys.argv[1])
    needles = xdfile.load_corpus(*sys.argv[2:])

    for i, needle in enumerate(needles.values()):
        print >>sys.stderr, "\r% 3d/%d %s" % (i, len(needles), needle),
        dups = find_similar_to(needle, corpus.values())
        for pct, a, b, answers in sorted(dups):
            print a, b, int(pct * 100), len(answers)

if __name__ == "__main__":
    main()
