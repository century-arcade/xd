#!/usr/bin/env python

import os
import os.path
import datetime
import zipfile
import urllib2

metafmt = """
Issued: %s
Acquired: %s
Source: %s
"""

logs = []

def log(s):
    print s
    logs.append(s)

# not including the from_date
def get_dates_between(from_date, to_date, days_to_advance=None):
    if not days_to_advance:
        days_to_advance = 1

    if from_date == to_date:
        return [ ]
    elif from_date > to_date:
        temp = from_date
        from_date = to_date
        to_date = from_date

    days_diff = (to_date - from_date).days + 1
    return [from_date + datetime.timedelta(days=x) for x in range(days_to_advance, days_diff, days_to_advance)]

def parse_date_from_filename(fn):
    import re
    m = re.search("(\w*)([12]\d{3})-(\d{2})-(\d{2})", fn)
    if m:
        abbr, y, mon, d = m.groups()
        return datetime.date(int(y), int(mon), int(d))

def zipwrite(zf, fn, data):
    zi = zipfile.ZipInfo(fn, datetime.datetime.now().timetuple()) # use 'now' as the filetime
    zi.external_attr = 0444 << 16L
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, data)

def main():
    today = datetime.datetime.today()
    today = datetime.date(today.year, today.month, today.day)
    todaystr = today.strftime("%Y-%m-%d")

    import argparse
    parser = argparse.ArgumentParser(description='download recent puzzles')

    parser.add_argument('-s', '--sources', dest='sources', default="puzzle-sources.txt", help='puzzle source descriptions')
    parser.add_argument('-c', '--corpus', dest='corpus_dir', default="crosswords", help='corpus directory')
    parser.add_argument('-o', '--output', dest='output', default=todaystr + "-raw.zip", help='output .zip file')
    parser.add_argument('-p', '--publisher', dest='publisher', default=None, help='only do one publisher')
    args = parser.parse_args()

    rawzf = zipfile.ZipFile(args.output, 'w')

    for L in file(args.sources).readlines():
        L = L.strip()
        if L.startswith("#"): # ignore comment lines
            continue

        ndaystr, ext, abbrid, pubdir, urlfmt = L.split()
        ndays = int(ndaystr)

        if args.publisher:
            if abbrid != args.publisher and pubdir != args.publisher:
                continue  # only do one publisher if given

        # check the corpus for the last date imported
        existing_dates = set()
        for thisdir, subdirs, files in os.walk(os.path.join(args.corpus_dir, pubdir)):
            for fn in files:
                if fn.startswith(abbrid) and fn.endswith(".xd"):
                    d = parse_date_from_filename(fn)
                    if d:
                        existing_dates.add(d)

        latest_date = max(existing_dates)

        # try to download dates since then
        # save all new downloads into one .zip
        for d in get_dates_between(latest_date, today, ndays):
            url = d.strftime(urlfmt)

            datestr = d.strftime("%Y-%m-%d")
            fndatestr = d.strftime("%Y/" + abbrid + "%Y-%m-%d")
            rawfn = "crosswords/%s/%s.%s" % (pubdir, fndatestr, ext)
            metafn = "crosswords/%s/%s-meta.txt" % (pubdir, fndatestr)

            try:
                print pubdir, abbrid, url
                response = urllib2.urlopen(url)

                zipwrite(rawzf, rawfn, response.read())

                # include -meta.txt in that .zip to provide exact source for each puzzle
                zipwrite(rawzf, metafn, metafmt % (datestr, todaystr, url))

            except (urllib2.HTTPError, urllib2.URLError) as err:
                log('[%s] %s: %s' % (err.code, err.reason, url))
            except Exception, e:
                log('[unknown] %s: %s' % (e, url))

    zipwrite(rawzf, todaystr + "-download.log", "\n".join(logs) + "\n")

if __name__ == "__main__":
    main()
