#!/usr/bin/env python

import sys
import os.path
import mkwww
import xdfile

outlines = [ ]
total_xd = 0
for metafn in sys.argv[1:]:
    pubxd = xdfile.xdfile(file(metafn).read(), metafn)

    num_xd = int(pubxd.get_header("num_xd"))
    total_xd += num_xd
    years = pubxd.get_header("years")
    pubid = metafn.split("/")[-2]

    outlines.append((num_xd, '<li><a href="{pubid}"><b>{pubid}</b></a>: {num_xd} crosswords from {years}</li>'.format(**{
        'pubid': pubid,
        "num_xd": num_xd,
        "years": years
        })))

out = mkwww.html_header.format(title="xd corpus grid similarity results")
out += "xd corpus has %d crosswords total:" % total_xd
out += "\n".join(L for n, L in sorted(outlines, reverse=True))

out += mkwww.html_footer

print out
