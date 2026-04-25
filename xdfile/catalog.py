
import re

from xdfile import utils
from xdfile import metadatabase as metadb
import xdfile

PUBREGEX_TSV = 'gxd/pubregex.tsv'


def get_publication(xd):
    matching_publications = set()

    all_headers = xd.get_header("Copyright").lower()

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

# some regex heuristics for shelving
_pubregex_cache = None

def _load_pubregex():
    global _pubregex_cache
    if _pubregex_cache is None:
        try:
            _pubregex_cache = list(utils.parse_tsv_data(open(PUBREGEX_TSV, 'r').read()))
        except FileNotFoundError:
            utils.error("File not exists: %s" % PUBREGEX_TSV, severity='WARNING')
            _pubregex_cache = []
    return _pubregex_cache


def find_pubid(rowstr):
    '''rowstr is a concatenation of all metadata fields.

    Two-stage match:
      1. pubregex.tsv (explicit overrides and aliases) — wins if any row matches
      2. implicit `<pubid>(\\d|-)` against every PublicationAbbr in publications.tsv

    Returns None if no match, or if the winning stage produces multiple matches.
    '''
    explicit = set()
    for r in _load_pubregex():
        if re.search(r['regex'], rowstr, flags=re.IGNORECASE):
            explicit.add(r['pubid'])

    if len(explicit) == 1:
        return explicit.pop()
    if len(explicit) > 1:
        utils.warn("%s: too many pubregex matches (%s)" % (rowstr, " ".join(explicit)))
        return None

    implicit = set()
    for pubid in metadb.xd_publications().keys():
        if re.search(r'%s(\d|-)' % re.escape(pubid), rowstr, flags=re.IGNORECASE):
            implicit.add(pubid)

    if len(implicit) == 1:
        return implicit.pop()
    if len(implicit) > 1:
        utils.warn("%s: too many implicit pubid matches (%s)" % (rowstr, " ".join(implicit)))
        return None

    utils.warn("%s: no pubid match" % rowstr)
    return None



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


def deduce_xdid(xd, mdtext):

    pubid = find_pubid(mdtext)
    if not pubid:
        publication = get_publication(xd)
        if publication:
            pubid = publication.PublicationAbbr
        else:
            return None

    num = xd.get_header('Number')
    if num:
        return "%s-%03d" % (pubid, int(num))

    dt = xd.get_header("Date")
    if dt:
        # year = xdfile.year_from_date(dt)
        return "%s%s" % (pubid, dt)


def get_shelf_path(xd, pubid, mdtext):
    publisher = ""
    if not pubid:
        pubid = find_pubid(mdtext)

    if pubid:
        publ = metadb.xd_publications()[pubid]
    else:
        publ = get_publication(xd)
        if publ:
            pubid = publ.PublicationAbbr
        else:
            return None

    if not pubid:
        utils.warn("unknown pubid for '%s'" % xd.filename)
        return None

    publisher = publ.PublisherAbbr

    num = xd.get_header('Number')
    if num:
        return "%s/%s-%03d" % (publisher or pubid, pubid, int(num))

    dt = xd.get_header("Date")
    if not dt:
        utils.warn("neither Number nor Date for '%s'" % xd.filename)
        return 'misc/' + xd.filename

    year = xdfile.year_from_date(dt)
    return "%s/%s/%s%s" % (publisher, year, pubid, dt)

