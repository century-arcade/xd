
import re

from xdfile import utils
from xdfile import metadatabase as metadb
import xdfile

def get_publication(xd):
    matching_publications = set()

    all_headers = "|".join(hdr for hdr in list(xd.headers.values())).lower()

    # source filename/metadata must be the priority
    abbr = utils.parse_pubid(xd.filename)

    all_pubs = metadb.xd_publications()

    for publ in all_pubs.values():
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

    return sorted(matching_pubs)[0][1]


# all but extension
def deduce_set_seqnum(xd):
    # look to filename
    base = utils.parse_pathname(xd.filename).base

    # check for date
    dt = utils.parse_date_from_filename(base)  # datetime object
    if dt:
        xd.set_header("Date", dt)
    else:
        # check for number in full path (eltana dir had number)
        m = re.search(r'(\d+)', xd.filename)
        if m:
            xd.set_header("Number", int(m.group(1)))


def get_shelf_path(xd, pubid):
    if not pubid:
        # determine publisher/publication
        try:
            publ = get_publication(xd)
        except Exception as e:
            publ = None
            if utils.get_args().debug:
                raise

        if publ and not pubid:
            pubid = publ.PublisherAbbr

        if not pubid:
            raise xdfile.NoShelfError("unknown pubid for '%s'" % xd.filename)

    num = xd.get_header("Number")
    if num:
        return "%s/%s-%03d" % (pubid, pubid, int(num))

    dt = xd.get_header("Date")
    if not dt:
        raise xdfile.NoShelfError("neither Number nor Date for '%s'" % xd.filename)

    year = xdfile.year_from_date(dt)
    return "%s/%s/%s%s" % (pubid, year, pubid, dt)

