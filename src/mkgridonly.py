#!/usr/bin/env python

# generates xd-grids-2016.xdz as a .zip file

import zipfile
import xdfile
import os

if __name__ == "__main__":
    corpus = xdfile.main_load()
    outfn = "xd-grids-2016.xdz"

    outzf = zipfile.ZipFile(outfn, "w")

    for fn, xd in sorted(corpus.items()):
        xdstr = xd.to_unicode(emit_clues=False)
        abbrid, d = xdfile.parse_date_from_filename(xd.filename)
        if d:
            year = max(d.year, 1980)
            month = d.month
            day = d.day
        else:
            year = 1980
            month = 1
            day = 1

        zi = zipfile.ZipInfo(xd.filename, (year, month, day, 9, 0, 0))
        zi.external_attr = 0444 << 16L
        zi.compress_type = zipfile.ZIP_DEFLATED
        outzf.writestr(zi, xdstr.encode("utf-8"))

