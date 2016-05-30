
import re

from xdfile import utils
from xdfile import metadatabase as metadb

def get_publication(xd):
    matching_publications = set()

    all_headers = "|".join(hdr for hdr in list(xd.headers.values())).lower()

    # source filename/metadata must be the priority
    abbr = utils.parse_pubid_from_filename(xd.filename)

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
def get_target_basename(xd, pubid):
    # determine publisher/publication
    try:
        publ = get_publication(xd)
    except Exception as e:
        publ = None
        if utils.get_args().debug:
            raise

    year = ""

    dt = xd.get_header("Date")  # string
    if dt:
        year = xdfile.year_from_date(dt)

    if xd.get_header("Number"):
        seqnum = xd.get_header("Number")
    else:
        seqnum = dt

    if not seqnum:  # no number or date in metadata
        # look to filename
        base = utils.parse_pathname(xd.filename).base

        # check for date
        dt = utils.parse_date_from_filename(base)  # datetime object
        if dt:
            seqnum = dt
        else:
            # check for number in full path (eltana dir had number)
            m = re.search(r'(\d+)', xd.filename)
            if m:
                seqnum = int(m.group(1))
            else:
                seqnum = None

    if publ and not pubid:
        pubid = publ.PublisherAbbr

    if pubid and seqnum:
        if year:
            return "%s/%s/%s%s" % (pubid, year, pubid, seqnum)
        return "%s/%s-%03d" % (pubid, pubid, seqnum)

    utils.log("pubid='%s', seqnum='%s'" % (pubid, seqnum))
    raise Exception("unknown shelf for '%s'" % xd.filename)

