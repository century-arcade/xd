#!/usr/bin/env python

import sys

all_files = set()
for filename in sys.argv[1:]:
    for line in file(filename).read().splitlines():
        if line:
            try:
                fn1, fn2 = line.split()[:2]
                all_files.add(fn1)
                all_files.add(fn2)
            except IndexError:
                print "ERROR in %s: %s" % (inputfn, line)

print " ".join(sorted(all_files))
