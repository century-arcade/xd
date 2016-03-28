#!/usr/bin/env python

import xdfile
import downloadraw

corpus = xdfile.main_load()

publishers = { }

for filename, xd in sorted(corpus.items()):
    xdfile.clean_headers(xd)

    abbrid, d = xdfile.parse_date_from_filename(filename)
    pubid = xd.filename.split("/")[1]
    pub = xd.get_header("Publisher") or xd.get_header("Copyright")
  
    if abbrid not in publishers:
        v = {
            "pubid": pubid,
            "dates": set(),
            "rights": set(),
            "editors": set(),
            "authors": set(),
            "num": set(),
         }
        publishers[abbrid] = v
    else:
        v = publishers[abbrid]

    
    v["rights"].add(xd.get_header("Copyright"))
    v["editors"].add(xd.get_header("Editor"))
    v["authors"].add(xd.get_header("Author"))
    v["num"].add(xd.filename)

    if d:
        v["dates"].add(d.strftime("%Y-%m-%d"))

def clean(s):
    try:
        s.remove(None)
    except:
        pass
    try:
        s.remove("")
    except:
        pass


print "\t".join("pubid pubabbr Publisher Editors FirstDateIssued LastDateIssued #Issued".split())

for abbrid, v in publishers.items():
    dates = v["dates"]
    clean(dates)
    clean(v.get("rights"))
    clean(v.get("editors"))
    print "\t".join([
        v.get("pubid"),
        abbrid,
        "|".join(sorted(v.get("rights"))).encode("utf-8"),
        "|".join(sorted(v.get("editors"))).encode("utf-8"),
        dates and ("<%s" % min(dates)) or "",
        dates and ("%s>" % max(dates)) or "",
        dates and ("%s+" % len(v.get("num"))) or "",
    ])    

