#!/usr/bin/python

import urllib2
from datetime import date, datetime, timedelta
import sys
import os
import os.path

#constants
DAILY_PUZZLE_URL = 'http://www.xwordinfo.com/PS?date=%s'
OUTPUT_DIR = "."

def info(s):
    print s

def error(s):
    print s

# utils
def get_html_content(url):
    try:
        response = urllib2.urlopen(url)
        return response.read()
    except urllib2.HTTPError, err:
        error("HTTP Error: %s ; URL: %s" %(err.code, url))
    except urllib2.URLError, err:
        error("URL Error: %s ; URL: %s" %(err.reason, url))

def main(dates):
    for d in dates:
        puzzle_url = DAILY_PUZZLE_URL % d.strftime("%Y/%m/%d")
        html_file = os.path.join(OUTPUT_DIR, "%s.html" % d.strftime("%Y-%m-%d"))

        if os.path.exists(html_file):
            continue

        info("Downloading %s to %s" % (puzzle_url, html_file))
        html_content = get_html_content(puzzle_url)

        with open(html_file, 'w') as local_file:
            local_file.write(html_content)

d1 = datetime.strptime(sys.argv[1], "%Y-%m-%d")
d2 = datetime.strptime(sys.argv[2], "%Y-%m-%d")

# this will give you a list containing all of the dates
dd = [d1 + timedelta(days=x) for x in range(1, (d2-d1).days + 1)]

main(dd)
