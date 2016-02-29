#!/usr/bin/env python

import sys

all_files = set()
for inputfn in sys.argv[1:]:
    for line in file(inputfn).read().splitlines():
        if not line: continue
        parts = line.strip().split(' ', 2)
        if len(parts) == 2:
            fn1, fn2 = parts
        elif len(parts) == 3:
            fn1, fn2, rest = parts
        else:
            print "ERROR in %s: %s" % (inputfn, line)
            continue

        all_files.add(fn1)
        all_files.add(fn2)

print " ".join(sorted(all_files))
