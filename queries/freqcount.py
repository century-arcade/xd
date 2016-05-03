#!/usr/bin/env python

import xdfile
import string

freqdist = {}

ok = string.uppercase + string.digits + "#"

for xd in xdfile.corpus():
    for letter in u"".join(xd.grid):
        letter = letter.upper()
        freqdist[letter] = freqdist.get(letter, 0) + 1
        if letter not in ok:
            print(letter.encode("utf-8"), xd.filename)

for k, v in sorted(freqdist.items()):
    print(v, k.encode("utf-8"))
