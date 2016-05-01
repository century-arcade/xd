#!/usr/bin/env python
#
# Usage: $0 [-o <output-location>] <input>
#
#   Renames the <input> file(s) according to metadata (in .xd, .tsv, or filenameb)
#   Appends metadata row to puzzles.tsv
#

import string
import re

from xdfile import xdfile
from xdfile.metadatabase import xd_publications_meta
from xdfile.utils import get_args, find_files, parse_pathname, log, debug, get_log, open_output

badchars = """ "'\\"""


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

    all_headers = "|".join(hdr for hdr in xd.headers.values()).lower()

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
    except Exception, e:
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
            seqnum = m.group(1)
        else:
            seqnum = None

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
    args = get_args(desc='shelve .xd files in proper location')

    outf = open_output()
    outf.toplevel = "crosswords"

    all_filenames = set()

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents, fn)

            try:
                target_fn = get_target_basename(xd)
                real_target_fn = target_fn + ".xd"

                # append a, b, c, etc until finding one that hasn't been taken already
                i = 0
                while real_target_fn in all_filenames:
                    real_target_fn = target_fn + string.lowercase[i] + ".xd"
                    i += 1

                reencoding = xd.to_unicode().encode("utf-8")
                if reencoding != contents:
                    log("non-identical contents when re-encoded")

                all_filenames.add(real_target_fn)
                outf.write_file(real_target_fn, contents)
            except Exception, e:
                log("unshelveable: " + str(e))
                if args.debug:
                    raise

    log("%d puzzles in misc/" % len([ fn for fn in all_filenames if "misc/" in fn]))
    outf.write_file("cleaned.log", get_log().encode("utf-8"))


if __name__ == "__main__":
    main()
