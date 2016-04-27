#!/usr/bin/env python
# -*- coding: utf-8
#
# Usage: $0 [-o <output-location>] <input>
#
#   Cleans headers in .xd files, according to some heuristics discovered from many thousands of real .puz files.
#   [?Generates a cleaned-metadata.tsv with original and cleaned headers for side-by-side comparison.]
#

import re
import zipfile
import datetime

from xdfile import xdfile, HEADER_ORDER
from xdfile.metadatabase import xd_publications_meta
from xdfile.utils import get_args, find_files, parse_pathname, log, get_log, zip_append


# from original filename
def parse_date_from_filename_old(fn):
    m = re.search("([A-Za-z]*)[_\s]?(\d{2,4})-?(\d{2})-?(\d{2})(.*)\.", fn)
    if m:
        abbr, yearstr, monstr, daystr, rest = m.groups()
        year, mon, day = int(yearstr), int(monstr), int(daystr)
        if len(yearstr) == 2:
            if year > 1900:
                pass
            elif year > 18:
                year += 1900
            else:
                year += 2000
        assert len(abbr) <= 5, abbr
        assert mon >= 1 and mon <= 12, "bad month %s" % monstr
        assert day >= 1 and day <= 31, "bad day %s" % daystr
        return datetime.date(year, mon, day)


def clean_year(year):
    if year > 1900:
        pass
    elif year > 18:
        year += 1900
    else:
        year += 2000
    assert year > 1920 and year < 2017, "bad year %s" % year
    return year

def parse_date_from_filename(fn):
    m = re.search("(\d+)", fn)
    if m:
        datestr = m.group(1)
        if len(datestr) == 6:
            try:
                # YYMMDD first
                year = clean_year(int(datestr[0:2]))
                mon = int(datestr[2:4])
                day = int(datestr[4:6])
                dt = datetime.date(year, mon, day)
                return dt
            except Exception, e:
                log(str(e))

            try:
                # then MMDDYY
                mon = int(datestr[0:2])
                day = int(datestr[2:4])
                year = clean_year(int(datestr[4:6]))
                dt = datetime.date(year, mon, day)
                return dt
            except Exception, e:
                log(str(e))


def clean_headers(xd):
    for hdr in xd.headers.keys():
        if hdr in ["Source", "Identifier", "Acquired", "Issued", "Category"]:
            xd.set_header(hdr, None)
        else:
            if hdr.lower() not in HEADER_ORDER:
                log("%s: '%s' header not known: '%s'" % (xd.filename, hdr, xd.headers[hdr]))

    title = xd.get_header("Title") or ""
    author = xd.get_header("Author") or ""
    editor = xd.get_header("Editor") or ""
    rights = xd.get_header("Copyright") or ""

    if author:
        r = r'(?i)(?:(?:By )*(.+)(?:[;/,-]|and) *)?(?:edited|Editor|(?<!\w)Ed[.])(?: By)*(.*)'
        m = re.search(r, author)
        if m:
            author, editor = m.groups()

        if author:
            while author.lower().startswith("by "):
                author = author[3:]

            while author[-1] in ",.":
                author = author[:-1]
        else:
            author = ""

        if " / " in author:
            if not editor:
                author, editor = author.rsplit(" / ", 1)

    if editor:
        while editor.lower().startswith("by "):
            editor = editor[3:]

        while editor[-1] in ",.":
            editor = editor[:-1]

    author = author.strip()
    editor = editor.strip()

    if title.endswith(']'):
        title = title[:title.rfind('[')]

    # title is only between the double-quotes for some USAToday
    if title.startswith("USA Today"):
        if title and title[-1] == '"':
            newtitle = title[title.index('"') + 1:-1]
            if newtitle[-1] == ",":
                newtitle = newtitle[:-1]
        elif title and title[0] == '"':
            newtitle = title[1:title.rindex('"')]
        else:
            newtitle = title

        xd.set_header("Title", newtitle)

#    rights = rights.replace(u"©", "(c)")

    xd.set_header("Author", author)
    xd.set_header("Editor", editor)
    xd.set_header("Copyright", rights)

    if not xd.get_header("Date"):
        try:
            d = parse_date_from_filename(xd.filename)
            if not d:
                d = parse_date_from_filename_old(xd.filename)

            if d:
                xd.set_header("Date", d.strftime("%Y-%m-%d"))
        except Exception, e:
            log(str(e))


def main():
    args = get_args(desc='clean metadata in a corpus of .xd puzzles')

    outzf = zipfile.ZipFile(args.output, 'w', allowZip64=True)

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents, fn)
            clean_headers(xd)
            zip_append(outzf, xd.filename, xd.to_unicode().encode("utf-8"))
        
    zip_append(outzf, "cleaned.log", get_log().encode("utf-8"))


if __name__ == "__main__":
    main()

