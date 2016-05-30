#!/usr/bin/env python3

# Usage: $0 [-o <puzzles.tsv>] <input>
#
#   Generates puzzles.tsv with cleaned metadata for each .xd in <input>.  
#

from xdfile import utils, metadatabase
import xdfile
import re

def find_date(s):
    m = re.search(r"\s*(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)?\s*(\d{1,2})?,?\s*\d{4},?\s*", s, flags=re.IGNORECASE)
    if m:
        return m.group(0)

    m = re.search(r"\d{2}[/\-]?\d{2}[/\-]?\d{2,4}", s)
    if m:
        return m.group(0)

    return ""


def clean_copyright(copyright, author):
    import re
    if author:
        copyright = copyright.replace(author, "")

    # and remove textual date
    dt = find_date(copyright)
    if dt:
        copyright = copyright.replace(dt, " ")

    return copyright


def clean_headers(xd):
    author = xd.get_header("Author") or ""

    if xd.get_header("Creator"):
        assert not author
        author = xd.get_header("Creator")
        xd.set_header("Creator", None)
    else:
        author = xd.get_header("Author") or ""

    title = xd.get_header("Title") or ""
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

    dt = xd.get_header("Date")

    # try getting Date from filename
    if not dt:
        try:
            d = utils.parse_date_from_filename(xd.filename)
            if d:
                dt = d.strftime("%Y-%m-%d")
        except Exception as e:
            utils.log(str(e))

    # try getting Date from copyright
    if not dt:
        dt = find_date(rights)

    if dt:
        xd.set_header("Date", dt)

    xd.set_header("Copyright", clean_copyright(rights, author))


    # make sure header fields are all known
    for hdr in list(xd.headers.keys()):
        if hdr in ["Source", "Identifier", "Acquired", "Issued", "Category"]:
            xd.set_header(hdr, None)
        else:
            if hdr.lower() not in xdfile.HEADER_ORDER:
                utils.log("%s: '%s' header not known: '%s'" % (xd.filename, hdr, xd.headers[hdr]))



def main():
    args = utils.get_args(desc='outputs cleaned puzzle metadata rows')

    outf = utils.open_output()

    outf.write(metadatabase.xd_puzzles_header)

    for input_source in args.inputs:
        for fn, contents in utils.find_files(input_source, ext='.xd'):
            xd = xdfile.xdfile(contents.decode('utf-8'), fn)
            clean_headers(xd)
            outf.write(metadatabase.xd_puzzles_row(xd))


if __name__ == "__main__":
    main()
