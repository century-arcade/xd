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

from xdfile.metadatabase import xd_publications, xd_puzzles_row, xd_puzzles_header, xd_puzzles_append, xd_receipts
from xdfile.utils import get_args, find_files, parse_pathname, log, debug, open_output, strip_toplevel, parse_tsv_data, parse_pubid_from_filename
from xdfile import catalog, utils
from xdfile import xdfile, HEADER_ORDER


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
            d = utils.parse_date_from_filename(xd.filename)
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


def main():
    global args
    args = get_args(desc='clean metadata and shelve .xd files in proper location')

    outf = open_output()
    assumed_toplevel = outf.toplevel
    outf.toplevel = "gxd"

    all_receipts = {}  # input files
    all_filenames = set()  # shelved files

    for xsvfn, xsvdata in find_files(*args.inputs, ext='sv'):
        for row in parse_tsv_data(xsvdata.decode("utf-8"), "SourceFile"):
            if row.SourceFilename in all_receipts:
                log("WARNING: double receipts!  not replacing.")
                continue 
            all_receipts[parse_pathname(row.SourceFilename).base] = row

    if not all_receipts:
        log("no files to shelve")
        return

    # to compare raw/cleaned headers side-by-side
    raw_tsv = ''

    # local puzzles.tsv for newly shelved files (rows can simply be appended to global puzzles.tsv)
    puzzles_tsv = ''

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents.decode("utf-8"), fn)

            rcptid = all_receipts[parse_pathname(fn).base].ReceiptId

            raw_tsv += xd_puzzles_row(xd, rcptid)

            clean_headers(xd)

            puzzles_tsv += xd_puzzles_row(xd, rcptid)

            try:
                target_fn = catalog.get_target_basename(xd)
                real_target_fn = target_fn + ".xd"

                # append a, b, c, etc until finding one that hasn't been taken already
                i = 0
                while real_target_fn in all_filenames:
                    real_target_fn = target_fn + string.ascii_lowercase[i] + ".xd"
                    i += 1

                all_filenames.add(real_target_fn)

                outf.write_file(real_target_fn, xd.to_unicode())
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

#    outf.write_file("cleaned-puzzles.tsv", xd_puzzles_header + puzzles_tsv)
#    outf.write_file("raw-puzzles.tsv", xd_puzzles_header + raw_tsv)


if __name__ == "__main__":
    main()
