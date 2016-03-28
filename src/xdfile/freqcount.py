#!/usr/bin/env python

import xdfile
import string

freqdist = { }
corpus = xdfile.main_load()

ok = string.uppercase + string.digits + "#"

for fn, xd in corpus.items():
    for letter in u"".join(xd.grid):
        letter = letter.upper()
        freqdist[letter] = freqdist.get(letter, 0) + 1
        if letter not in ok:
            print letter.encode("utf-8"), fn

for k, v in sorted(freqdist.items()):
    print v, k.encode("utf-8")
