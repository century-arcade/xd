#!/usr/bin/env python
#
# Usage: $0 [-o <output-location>] <input>
#
#   Renames the <input> file(s) according to metadata (in .xd, .tsv, or filenameb)
#   Appends metadata row to puzzles.tsv
#

import string
import re
import zipfile

from xdfile import xdfile
from xdfile.metadatabase import xd_publications_meta
from xdfile.utils import get_args, find_files, parse_pathname, log, get_log, zip_append

badchars = """ "'\\"""


def clean_filename(fn):
    basefn = parse_pathname(fn).base
    for ch in badchars:
        basefn = basefn.replace(ch, '_')
    return basefn


def parse_pubid_from_filename(fn):
    m = re.search("(^[A-Za-z]*)", fn)
    return m.group(1)


def get_publication(xd):
    matching_publications = set()

    all_headers = "|".join(hdr for hdr in xd.headers.values()).lower()

    abbr = parse_pubid_from_filename(xd.filename)

    all_pubs = xd_publications_meta()

    for publ in all_pubs:
        if publ.PublicationAbbr == abbr.lower():
            matching_publications.add(publ)

        if publ.PublicationName and publ.PublicationName.lower() in all_headers:
            matching_publications.add(publ)

        if publ.PublisherName and publ.PublisherName.lower() in all_headers:
            matching_publications.add(publ)

    if not matching_publications:
        return None
    elif len(matching_publications) == 1:
        return matching_publications.pop()

    # otherwise, filter out 'self' publications
    matching_pubs = set([p for p in matching_publications if 'self' not in p.PublisherAbbr])

    if len(matching_pubs) == 1:
        return matching_pubs.pop()

    log("%s: pubs=%s; headers=%s" % (xd, " ".join(p.PublicationAbbr for p in matching_pubs or matching_publications), all_headers))


def get_target_filename(xd):
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
        return "misc/%s.xd" % clean_filename(xd.filename)

    return "crosswords/%s%s.xd" % (publabbr, seqnum)



def main():
    global args
    args = get_args(desc='shelve .xd files in proper location')

    if args.output:
        outzf = zipfile.ZipFile(args.output, 'w', allowZip64=True)
    else:
        outzf = None

    all_filenames = set()

    for input_source in args.inputs:
        for fn, contents in find_files(input_source, ext='.xd'):
            xd = xdfile(contents, fn)

            try:
                target_fn = get_target_filename(xd)
                real_target_fn = target_fn
                i = 0
                while real_target_fn in all_filenames:
                    real_target_fn = target_fn + string.lowercase[i]
                    i += 1

                reencoding = xd.to_unicode().encode("utf-8")
                if reencoding != contents:
                    log("non-identical contents when re-encoded")

                all_filenames.add(real_target_fn)
                if outzf:
                    zip_append(outzf, real_target_fn, contents)
                else:
                    log("would store to '%s'" % real_target_fn)
            except Exception, e:
                log("unshelveable: " + str(e))
                if args.debug:
                    raise

    log("%d puzzles in misc/" % len([ fn for fn in all_filenames if fn.startswith("misc")]))
    if outzf:
        zip_append(outzf, "cleaned.log", get_log().encode("utf-8"))

"""
def save_file(xd, outf):
    outfn = xd.filename

    xdstr = xd.to_unicode().encode("utf-8")

    # check for duplicate filename and contents

    xdhash = hash(xdstr)

    while outfn in all_files:
        if all_files[outfn] == xdhash:
            log("exact duplicate")
            return

        log("same filename, different contents: '%s'" % outfn)
        outfn += ".2"

    all_files[outfn] = xdhash

    if xdhash in all_hashes:
        log("duplicate contents of %s" % all_hashes[xdhash])
    else:
        all_hashes[xdhash] = outfn

    # write to output

    if isinstance(outf, zipfile.ZipFile):
        if year < 1980:
            year = 1980
        zi = zipfile.ZipInfo(outfn, (year, month, day, 9, 0, 0))
        zi.external_attr = 0444 << 16L
        zi.compress_type = zipfile.ZIP_DEFLATED
        outf.writestr(zi, xdstr)
    elif isinstance(outf, file):
        outf.write(xdstr)
    else:
        try:
            basedirs, fn = os.path.split(outfn)
            os.makedirs(basedirs)
        except:
            pass
        file(outfn, "w-").write(xdstr)
"""

if __name__ == "__main__":
    main()
