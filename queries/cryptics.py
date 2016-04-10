#!/usr/bin/env python

import xdfile

for xd in xdfile.corpus():
    for k, v in xd.headers.items():
        if "cryptic" in v.lower():
            print xd, v.encode("utf-8")
            break

