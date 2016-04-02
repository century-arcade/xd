#!/usr/bin/env python

from __future__ import print_function

import xdfile

print(xdfile.xd_metadata_header())

for xd in xdfile.corpus():
    try:
        xdfile.clean_headers(xd)
        print(xdfile.xd_metadata(xd))
    except Exception, e:
        xdfile.log("%s: %s" % (xd.filename, e))
        raise
