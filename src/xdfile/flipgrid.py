#!/usr/bin/env python

import xdfile


def get_col(g, n):
    return "".join([r[n] for r in g])


def flipgrid(xd):
    flipxd = xdfile.xdfile()
    flipxd.filename = "transposed/" + xd.filename
    flipxd.headers = xd.headers.copy()
    g = []
    for i in xrange(len(xd.grid[0])):
        try:
            g.append(get_col(xd.grid, i))
        except:
            print xd

    flipxd.grid = g

    for posdir, posnum, answer in flipxd.iteranswers():
        flipxd.clues.append(((posdir, posnum), xd.get_clue_for_answer(answer), answer))

    flipxd.clues = sorted(flipxd.clues)
    return flipxd

if __name__ == "__main__":
    import sys
    import utils
    for fn, contents in utils.find_files(sys.argv[1]):
        flipped = flipgrid(xdfile.xdfile(contents, fn)).to_unicode().encode("utf-8")
        print flipped
        unflipped = flipgrid(xdfile.xdfile(flipped, fn)).to_unicode().encode("utf-8")
        print unflipped
        assert unflipped == contents
