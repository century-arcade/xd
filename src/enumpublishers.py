#!/usr/bin/env python

from __future__ import print_function

import xdfile

SEP = '\t'

def clean_set(s):
    try:
        s.remove(None)
    except:
        pass
    try:
        s.remove("")
    except:
        pass

class Publisher:
    def __init__(self, abbrid):
        self.abbrid = abbrid
        self.pubid = abbrid
        self.dates = set()
        self.rights = set()
        self.editors = set()
        self.authors = set()
        self.puzzles = set()

def publishers_header():
    print(SEP.join("pubid pubabbr Copyright #Issued Editors FirstDate LastDate".split()))

def publisher_line(pub):
    clean_set(pub.dates)
    clean_set(pub.rights)
    clean_set(pub.editors)
    for rights in sorted(pub.rights):
        print(SEP.join([
            pub.pubid,
            pub.abbrid,
            rights,
            str(len(pub.puzzles)),
            "|".join(sorted(pub.editors)).encode("utf-8"),
            pub.dates and ("%s" % min(pub.dates)) or "",
            pub.dates and ("%s" % max(pub.dates)) or ""
        ]).encode("utf-8"))

def main():
    publishers = {}

    for xd in xdfile.corpus():
        abbrid, d = xdfile.parse_date_from_filename(xd.filename)
        pubid = xd.filename.split("/")[1]
        pubname = xd.get_header("Publisher") or xd.get_header("Copyright")

        if pubname not in publishers:
            pub = Publisher(abbrid)
            publishers[pubname] = pub
        else:
            pub = publishers[pubname]

        pub.abbrid = abbrid
        pub.rights.add(xd.get_header("Copyright"))
        pub.editors.add(xd.get_header("Editor"))
        pub.authors.add(xd.get_header("Author"))
        pub.puzzles.add(xd)

        if d:
            pub.dates.add(d.strftime("%Y-%m-%d"))

    publishers_header()

    for pubname, pub in publishers.items():
        publisher_line(pub)

main()

