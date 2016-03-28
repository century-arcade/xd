#!/usr/bin/env python

import xdfile

def get_col(g, n):
    return "".join([ r[n] for r in g ])

def flipgrid(xd):
    flipxd = xdfile.xdfile()
    flipxd.headers = xd.headers.copy()
    g = [ ]
    for i in xrange(len(xd.grid[0])):
        g.append(get_col(xd.grid, i))

    flipxd.grid = g
    
    for pos, clue, answer in xd.clues:
        posdir, n = pos
        if posdir == 'A':
            posdir = 'D'
        elif posdir == 'D':
            posdir = 'A'

        flipxd.clues.append(((posdir, n), clue, answer))

    return flipxd

if __name__ == "__main__":
    import sys
    import utils
    for fn, contents in utils.find_files(sys.argv[1]):
        print flipgrid(xdfile.xdfile(contents, fn)).to_unicode().encode("utf-8")
