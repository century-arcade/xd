#!/usr/bin/env python

# Usage: $0 <scraper> <raw.zip> <xd.zip>
#
# Uses scraper to download and append missing entries to raw.zip
#  then uses scraper to translate all entries in raw.zip to xd.zip


import os.path
import zipfile
import re
import sys
import datetime
import errors
from utils import DateUtils, ZipUtils

def error(s):
    print s

def main():
    scrapername = sys.argv[1]
    inzipfn = sys.argv[2]
    outzipfn = sys.argv[3]

    # additional validations
    try:
        module = __import__("scrapers", fromlist=[scrapername])
        scraper = getattr(module, scrapername)()
    except (ImportError, AttributeError):
        error('unknown scraper "%s"' % scrapername)
        return

    sources = { } # [date] -> contents

    try:
        with zipfile.ZipFile(outzipfn, 'r') as outzf:
           files = [ zi.filename for zi in outzf.infolist() ]
    except:
        files = []

    print
    with zipfile.ZipFile(outzipfn, 'a') as outzf:
      with zipfile.ZipFile(inzipfn, 'r') as rawzf:
        for zi in rawzf.infolist():
            base, ext = os.path.splitext(zi.filename)
            zi.filename = base + ".xd"
            contents=rawzf.read(zi)
            if zi.filename in files:
                continue
            print "\r" + zi.filename,
            try:
                xdcontents = scraper.build_crossword(contents)
                outzf.writestr(zi, unicode(xdcontents).encode("utf-8"))
            except Exception, e:
                import traceback
                print
                print str(e)
                path, fn = os.path.split(base)
                file(fn + ".raw", 'w').write(contents)
                file(fn + ".xd", 'w').write(traceback.format_exc())
                
    print

if __name__ == "__main__":
    main()
