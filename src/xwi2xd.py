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
    infn = sys.argv[2]
    outfn = sys.argv[3]

    # additional validations
    try:
        module = __import__("scrapers", fromlist=[scrapername])
        scraper = getattr(module, scrapername)()
    except (ImportError, AttributeError):
        error('unknown scraper "%s"' % scrapername)
        return

    xdcontents = scraper.build_crossword(file(infn).read())
    file(outfn, 'w').write(unicode(xdcontents).encode("utf-8"))

if __name__ == "__main__":
    main()
