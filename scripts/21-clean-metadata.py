#!/usr/bin/env python3

# Usage: $0 [-o <puzzles.tsv>] <input>
#
#   Generates puzzles.tsv with cleaned metadata for each .xd in <input>.
#

from xdfile import utils, metadatabase as metadb
import xdfile
import re


CLEAN_SUFFIX = '_clean'


def find_date(s):
    m = re.search(r"\s*(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)?\s*(\d{1,2})?,?\s*\d{4},?\s*", s, flags=re.IGNORECASE)
    if m:
        return m.group(0)

    m = re.search(r"\d{2}[/\-]?\d{2}[/\-]?\d{2,4}", s)
    if m:
        return m.group(0)

    return ""


def boil_copyright(copyright, author):
    import re
    if author:
        copyright = copyright.replace(author, "")

    # and remove textual date
    dt = find_date(copyright)
    if dt:
        copyright = copyright.replace(dt, " ")

#    copyright = copyright.replace(u"©", "(c)")

    return copyright


# also editor
def clean_author(author, editor):
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
    return author, editor


def clean_title(title):
    if title.endswith(']'):
        title = title[:title.rfind('[')]

    # title is only between the double-quotes for some USAToday
    if title.startswith("USA Today"):
        if title and title[-1] == '"':
            title = title[title.index('"') + 1:-1]
            if title[-1] == ",":
                title = title[:-1]
        elif title and title[0] == '"':
            title = title[1:title.rindex('"')]

    return title


def clean_headers(xd):
    # remove known unwanted header fields, log unknown headers
    for hdr in list(xd.headers.keys()):
        if hdr in ["Source", "Identifier", "Acquired", "Issued", "Category"]:
            xd.set_header(hdr, None)
        else:
            if hdr.lower() not in xdfile.HEADER_ORDER:
                utils.warn("%s: '%s' header not known: '%s'" % (xd.filename, hdr, xd.headers[hdr]))

    # clean Author and Editor headers
    author = xd.get_header("Author") or ""
    if not author:
        if xd.get_header("Creator"):
            assert not author
            author = xd.get_header("Creator")
            xd.set_header("Creator", None)

    editor = xd.get_header("Editor") or ""

    newauthor, neweditor = clean_author(author, editor)

    if newauthor != author:
        xd.set_header("Author" + CLEAN_SUFFIX, newauthor)

    if neweditor != editor:
        xd.set_header("Editor" + CLEAN_SUFFIX, neweditor)

    # clean Title header
    title = xd.get_header("Title") or ""
    newtitle = clean_title(title)

    if newtitle != title:
        xd.set_header("Title" + CLEAN_SUFFIX, newtitle)
    # create Date header
    dt = xd.get_header("Date")

    ## try getting Date from filename
    if not dt:
        try:
            d = utils.parse_date_from_filename(xd.filename)
            if d:
                dt = d.strftime("%Y-%m-%d")
        except Exception as e:
            utils.error(str(e))
            if args.debug:
                raise

    ## try getting Date from copyright
    if not dt:
        rights = xd.get_header("Copyright") or ""
        dt = find_date(rights)

    if dt:
        xd.set_header("Date", dt)



def main():
    args = utils.get_args(desc='outputs cleaned puzzle metadata rows')

    for input_source in args.inputs:
        for fn, contents in utils.find_files(input_source, ext='.xd'):
            xd = xdfile.xdfile(contents.decode('utf-8'), fn)
            clean_headers(xd)
            metadb.update_puzzles_row(xd)


if __name__ == "__main__":
    main()
