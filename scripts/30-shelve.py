#!/usr/bin/env python3
# -*- coding: utf-8
#
# Usage: $0 [-o <output-location>] <input>
#
#   Cleans headers in .xd files, according to some heuristics discovered from many thousands of real .puz files.
#   Generates a raw-puzzles.tsv with original headers and cleaned-puzzles.tsv with cleaned headers for side-by-side comparison.
#   Renames the <input> file(s) according to metadata (in .xd, .tsv, or filenameb)
#   Appends cleaned metadata row to puzzles.tsv with correct ReceiptId from sources.tsv.
#

import string
import re
import datetime

from xdfile.metadatabase import xd_publications_meta, xd_puzzles_row, xd_puzzles_header, xd_puzzles_append, xd_receipts_meta
from xdfile.utils import get_args, find_files, parse_pathname, log, debug, get_log, open_output, strip_toplevel, parse_tsv_data
from xdfile import xdfile, HEADER_ORDER


badchars = """ "'\\"""


def construct_date(y, m, d):
    thisyear = datetime.datetime.today().year
    year, mon, day = int(y), int(m), int(d)

    if year > 1900 and year <= thisyear:
        pass
    elif year < 100:
        if year >= 0 and year <= thisyear - 2000:
            year += 2000
        else:
            year += 1900
    else:
        debug("year outside 1900-%s: '%s'" % (thisyear, y))
        return None

    if mon < 1 or mon > 12:
        debug("bad month '%s'" % m)
        return None

    if day < 1 or day > 31:
        debug("bad day %s" % d)
        return None

    return datetime.date(year, mon, day)


# from original filename
def parse_date_from_filename(fn):
    base = parse_pathname(fn).base
    m = re.search("(\d{2,4})-?(\d{2})-?(\d{2})", base)
    if m:
        g1, g2, g3 = m.groups()
        # try YYMMDD first, then MMDDYY
        return construct_date(g1, g2, g3) or construct_date(g3, g1, g2)


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
    xd.set_header("Copyright", rights)

    if not xd.get_header("Date"):
        try:
            d = parse_date_from_filename(xd.filename)
            if d:
                xd.set_header("Date", d.strftime("%Y-%m-%d"))
        except Exception as e:
            log(str(e))

    # make sure header fields are all known
    for hdr in list(xd.headers.keys()):
        if hdr in ["Source", "Identifier", "Acquired", "Issued", "Category"]:
            xd.set_header(hdr, None)
        else:
            if hdr.lower() not in HEADER_ORDER:
                log("%s: '%s' header not known: '%s'" % (xd.filename, hdr, xd.headers[hdr]))


def clean_filename(fn):
    basefn = parse_pathname(fn).base
    for ch in badchars:
        basefn = basefn.replace(ch, '_')
    return basefn


def parse_pubid_from_filename(fn):
    m = re.search("(^[A-Za-z]*)", parse_pathname(fn).base)
    return m.group(1)


def get_publication(xd):
    matching_publications = set()

    all_headers = "|".join(hdr for hdr in list(xd.headers.values())).lower()

    # source filename/metadata must be the priority
    abbr = parse_pubid_from_filename(xd.filename)

    all_pubs = xd_publications_meta()

    for publ in all_pubs:
        if publ.PublicationAbbr == abbr.lower():
            matching_publications.add((1, publ))

        if publ.PublicationName and publ.PublicationName.lower() in all_headers:
            matching_publications.add((2, publ))

        if publ.PublisherName and publ.PublisherName.lower() in all_headers:
            matching_publications.add((3, publ))

    if not matching_publications:
        return None
    elif len(matching_publications) == 1:
        return matching_publications.pop()[1]

    # otherwise, filter out 'self' publications
    matching_pubs = set([(pri, p) for pri, p in matching_publications if 'self' not in p.PublisherAbbr])

    if not matching_pubs:
        matching_pubs = matching_publications  # right back where we started
    elif len(matching_pubs) == 1:
        return matching_pubs.pop()[1]

    debug("%s: pubs=%s; headers=%s" % (xd, " ".join(p.PublicationAbbr for pri, p in matching_pubs), all_headers))

    return sorted(matching_pubs)[0][1]


# all but extension
def get_target_basename(xd):
    # determine publisher/publication
    try:
        publ = get_publication(xd)
    except Exception as e:
        publ = None
        if args.debug:
            raise

    # determine date (or at least year if possible)
    seqnum = xd.get_header("Date")
    if seqnum:
        year = seqnum.split("-")[0]
    else:
        year = ""
        m = re.search(r'(\d+)', xd.filename)
        if m:
            year = m.group(1)
        else:
            year = None

    if publ and seqnum:
        if year:
            publabbr = "%s/%s/%s" % (publ.PublisherAbbr, year, publ.PublicationAbbr)
        elif publ:
            publabbr = "%s/%s" % (publ.PublisherAbbr, publ.PublicationAbbr)
    else:
        return "misc/%s" % clean_filename(xd.filename)

    return "%s%s" % (publabbr, seqnum)


def main():
    global args
    args = get_args(desc='clean metadata and shelve .xd files in proper location')

    outf = open_output()
    assumed_toplevel = outf.toplevel
    outf.toplevel = "crosswords"

    all_receipts = {}  # input files
    all_filenames = set()  # shelved files

    for xsvfn, xsvdata in find_files(*args.inputs, ext='sv'):
        for row in parse_tsv_data(xsvdata.decode("utf-8"), "SourceFile"):
            assert row.SourceFilename not in all_receipts, "double receipts?"
            all_receipts[parse_pathname(row.SourceFilename).base] = row

    assert all_receipts, all_receipts

    # to compare raw/cleaned headers side-by-side
    raw_tsv = xd_puzzles_header

    # local puzzles.tsv for newly shelved files (rows can simply be appended to global puzzles.tsv)
    puzzles_tsv = xd_puzzles_header

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents.decode("utf-8"), fn)

            rcptid = all_receipts[parse_pathname(fn).base].ReceiptId

            raw_tsv += xd_puzzles_row(xd, rcptid)

            clean_headers(xd)

            puzzles_tsv += xd_puzzles_row(xd, rcptid)

            try:
                target_fn = get_target_basename(xd)
                real_target_fn = target_fn + ".xd"

                # append a, b, c, etc until finding one that hasn't been taken already
                i = 0
                while real_target_fn in all_filenames:
                    real_target_fn = target_fn + string.ascii_lowercase[i] + ".xd"
                    i += 1

                all_filenames.add(real_target_fn)

                outf.write_file(real_target_fn, xd.to_unicode().encode("utf-8"))
            except Exception as e:
                log("unshelveable: " + str(e))
                if args.debug:
                    raise

    misc_files =  [fn for fn in all_filenames if "misc/" in fn]
    if misc_files:
        log("%d puzzles in misc/" % len(misc_files))

    if not assumed_toplevel:
        # shelving directly into corpus
        xd_puzzles_append(puzzles_tsv)

    outf.write_file("cleaned-puzzles.tsv", xd_puzzles_header + puzzles_tsv)
    outf.write_file("raw-puzzles.tsv", raw_tsv)
    outf.write_file("shelved.log", get_log().encode("utf-8"))


if __name__ == "__main__":
    main()
