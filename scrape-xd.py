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
from utils.general import DateUtils, ZipUtils

def error(s):
    print s

def parse_fn(fn):
    m = re.match(r'crosswords-(\w+)/(\d+)/\1-\2-(\d+)-(\d+)', fn)
    if m:
        pub, y, mon, d = m.groups()
        return pub, datetime.date(int(y), int(mon), int(d))

def main():
    this_year = DateUtils.today().year
    last_date = DateUtils.today()

    scrapername = sys.argv[1]
    if len(sys.argv) > 2:
        this_year = int(sys.argv[2])
        last_date = datetime.date(this_year, 12, 31)

    # additional validations
    try:
        module = __import__("scrapers", fromlist=[scrapername])
        scraper = getattr(module, scrapername)()
    except (ImportError, AttributeError):
        error('unknown scraper "%s"' % scrapername)
        return

    inzipfn = '%s-%s-raw.zip' % (scrapername, this_year)
    outzipfn = '%s-%s-xd.zip' % (scrapername, this_year)
   
    sources = { } # [date] -> contents

    try:
        # read all raw sources
        with zipfile.ZipFile(inzipfn, 'r') as rawzf:
            for zi in rawzf.infolist():
                scrapername, t = parse_fn(zi.filename)
                sources[t] = rawzf.read(zi)
    except Exception, e:
        import traceback
        traceback.print_exc()

    print

    if sources:
        first_date = min(sources.keys())
    else:
        first_date = DateUtils.today()

    with zipfile.ZipFile(inzipfn, 'a') as rawzf:
      for date in DateUtils.get_dates_between(first_date, last_date):
        try:
            if date not in sources:
                print "downloading %s" % date
                content = scraper.get_content(date)
            else:
                content = ""
        except errors.ContentDownloadError:
            print '\tERROR: Content Download Error'
            continue
        except errors.NoCrosswordError:
            print '\tERROR: No Crossword for date'
            continue

        if content:
            filename = '%s-%s.%s' %(scrapername, DateUtils.to_string(date), scraper.RAW_CONTENT_TYPE)
            pathname = os.path.join('crosswords-%s' % scrapername, str(date.year), filename)
            ZipUtils.append(rawzf, content, pathname)

            sources[date] = content
     
    print

    outzf = zipfile.ZipFile(outzipfn, 'w')
    for t in sorted(sources.keys()):
        print ".",
        content = sources[t]
        filename = '%s-%s.xd' % (scrapername, DateUtils.to_string(t))
        pathname = os.path.join('crosswords-%s' % scrapername, str(t.year), filename)
        try:
            xdcontent = str(scraper.build_crossword(content))

            # append to zip archive
            ZipUtils.append(outzf, xdcontent, pathname, t)
        except:
#            file(filename + ".raw", 'w').write(content)
            import traceback
            traceback.print_exc()
            print "\tERROR parsing %s" % t # , saved as %s.raw" % (t, filename)

    print

if __name__ == "__main__":
    main()
