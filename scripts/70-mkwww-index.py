#!/usr/bin/env python3

import time
import sys
# import os.path
import mkwww
import xdfile

outlines = []
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

out = mkwww.html_header.format(title=time.strftime("xd corpus grid similarity results [%Y-%m-%d]"))
out += "The xd corpus has %d crosswords total:" % total_xd
out += "<ul>"
out += "\n".join(L for n, L in sorted(outlines, reverse=True))
out += "</ul>"
out += '<a href="xd-xdiffs.zip">xd-xdiffs.zip</a> (7MB) has raw data for all puzzles that are at least 25% similar.  Source code for using <a href="https://github.com/century-arcade/xd">the .xd format is available on Github.</a><br/>'
out += mkwww.html_footer

print(out)
