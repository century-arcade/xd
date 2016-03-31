#!/usr/bin/env python

import sys
import xdfile
import downloadraw

SEP = "\t"

print SEP.join(["pubid", "pubvol", "Date",
                "Title", "Author", "Editor"])

corpus = xdfile.main_load()

for filename, xd in sorted(corpus.items()):
    xdfile.clean_headers(xd)
    abbrid, d = downloadraw.parse_date_from_filename(xd.filename)
    pubid = xd.filename.split("/")[1]

    fields = [
        pubid,
        abbrid + str(d.year),
        xd.get_header("Date") or d.strftime("%Y-%m-%d"),
        xd.get_header("Title") or "",
        xd.get_header("Author") or "",
        xd.get_header("Editor") or "",
    ]

    assert SEP not in "".join(fields)
    try:
        print SEP.join(fields).encode("utf-8")
    except Exception:
        print >>sys.stderr, filename
        raise
