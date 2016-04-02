#!/usr/bin/env python

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
    def __init__(self, pubid):
        self.pubid = pubid
        self.dates = set()
        self.rights = set()
        self.editors = set()
        self.authors = set()
        self.num = set()

def publishers_header():
    print SEP.join("pubid pubabbr Publisher Editors FirstDateIssued LastDateIssued #Issued".split())

def publisher_line(pub):
    clean_set(pub.dates)
    clean_set(pub.rights)
    clean_set(pub.editors)
    print SEP.join([
        pub.pubid,
        abbrid,
        "|".join(sorted(pub.rights)).encode("utf-8"),
        "|".join(sorted(pub.editors)).encode("utf-8"),
        pub.dates and ("< %s" % min(pub.dates)) or "",
        pub.dates and ("%s >" % max(pub.dates)) or "",
        pub.dates and ("%s+" % len(pub.num)) or "",
    ])

def main():
    for filename, xd in sorted(xdfile.corpus()):
        abbrid, d = xdfile.parse_date_from_filename(filename)
        pubid = xd.filename.split("/")[1]
        pub = xd.get_header("Publisher") or xd.get_header("Copyright")

        if abbrid not in publishers:
            publishers[abbrid] = Publisher(abbrid)

        v = publishers[abbrid]

        v.rights.add(xd.get_header("Copyright"))
        v.editors.add(xd.get_header("Editor"))
        v.authors.add(xd.get_header("Author"))
        v.num.add(xd.filename)

        if d:
            v.dates.add(d.strftime("%Y-%m-%d"))

publishers = {}

publishers_header()

for abbrid, pub in publishers.items():
    publisher_line(pub)

