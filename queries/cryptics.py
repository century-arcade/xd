#!/usr/bin/env python

import xdfile

for xd in xdfile.corpus():
    grid = "".join([L.strip('#') for L in xd.grid])
    nblocks = len([x for x in grid if x == xdfile.BLOCK_CHAR])
    total = len(grid)
    print int(float(nblocks)*100/total), xd.size(), xd,

    for k, v in xd.headers.items():
        if "cryptic" in v.lower():
            print v.encode("utf-8"),
            break

    print
