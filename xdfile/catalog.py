
import hashlib
import re

from xdfile import utils
from xdfile import metadatabase as metadb
import xdfile

PUBREGEX_TSV = 'gxd/pubregex.tsv'
OVERRIDES_TSV = 'gxd/overrides.tsv'

# Provisional xdids carry the literal "unshelved-" substring as their discriminator.
# Two shapes:
#   no pubid resolved:        unshelved-<hash8>-<slug>
#   pubid resolved, no date:  <pubid>-unshelved-<hash8>-<slug>
PROVISIONAL_MARKER = "unshelved-"
_SLUG_RE = re.compile(r'[^a-z0-9-]')


def is_provisional(xdid):
    return bool(xdid) and PROVISIONAL_MARKER in xdid


def _parse_mdtext(mdtext):
    """mdtext is "|".join((ExternalSource, InternalSource, SourceFilename))."""
    parts = (mdtext or "").split("|", 2)
    while len(parts) < 3:
        parts.append("")
    return tuple(parts)


def _provisional_hash(extsrc, source_filename):
    return hashlib.sha1(("%s|%s" % (extsrc, source_filename)).encode("utf-8")).hexdigest()[:8]


def _provisional_slug(source_filename, max_len=20):
    base = utils.parse_pathname(source_filename).base.lower()
    cleaned = _SLUG_RE.sub('', base)
    return cleaned[:max_len] or 'x'


def _provisional_xdid(mdtext, pubid=None):
    extsrc, _, source_filename = _parse_mdtext(mdtext)
    h = _provisional_hash(extsrc, source_filename)
    slug = _provisional_slug(source_filename)
    if pubid:
        return "%s-%s%s-%s" % (pubid, PROVISIONAL_MARKER, h, slug)
    return "%s%s-%s" % (PROVISIONAL_MARKER, h, slug)


def provisional_path(xdid, extsrc):
    """Disk path (without .xd extension) for a provisional xdid."""
    if xdid.startswith(PROVISIONAL_MARKER):
        return "unshelved/%s/%s" % (extsrc or "unknown", xdid)
    pubid = xdid.split("-" + PROVISIONAL_MARKER, 1)[0]
    publ = metadb.xd_publications().get(pubid)
    publisher = publ.PublisherAbbr if publ else pubid
    return "%s/unshelved/%s" % (publisher, xdid)


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

    # Stable sort by (priority, PublicationAbbr); AttrDict isn't directly orderable.
    return sorted(matching_pubs, key=lambda x: (x[0], x[1].PublicationAbbr))[0][1]

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


# Per-source manual xdid pins. Format: ExternalSource, SourceFilename, xdid, note
_overrides_cache = None


def _load_overrides():
    global _overrides_cache
    if _overrides_cache is None:
        _overrides_cache = {}
        try:
            rows = list(utils.parse_tsv_data(open(OVERRIDES_TSV, 'r').read(), "Override"))
            for r in rows:
                if r.xdid:
                    _overrides_cache[(r.ExternalSource, r.SourceFilename)] = r.xdid
        except FileNotFoundError:
            pass
    return _overrides_cache


def lookup_xdid_override(extsrc, source_filename):
    """Return the manually-pinned xdid for this (ExternalSource, SourceFilename), or None."""
    return _load_overrides().get((extsrc, source_filename))


def shelf_path_from_xdid(xdid):
    """Derive shelf path (without .xd extension) from a real xdid string.
    Returns None if the xdid format isn't recognized."""
    # Date format: <pubid>YYYY-MM-DD
    m = re.match(r'^([a-z]+)\d{4}-\d{2}-\d{2}$', xdid)
    if m:
        pubid = m.group(1)
        publ = metadb.xd_publications().get(pubid)
        publisher = publ.PublisherAbbr if publ else pubid
        year = xdid[len(pubid):len(pubid) + 4]
        return "%s/%s/%s" % (publisher, year, xdid)
    # Number format: <pubid>-NNN
    m = re.match(r'^([a-z]+)-\d+$', xdid)
    if m:
        pubid = m.group(1)
        publ = metadb.xd_publications().get(pubid)
        publisher = publ.PublisherAbbr if publ else pubid
        return "%s/%s" % (publisher, xdid)
    return None


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
        # Number is the trailing digit run of the basename, optionally followed
        # by a single letter variant marker (e.g. "bg-002a"). Embedded digits
        # like year fragments ("wp92bms") or directory indices aren't sequence
        # numbers and shouldn't be guessed at.
        m = re.search(r'(\d+)[a-zA-Z]?$', base)
        if m:
            xd.set_header("Number", int(m.group(1)))


def resolve_pubid(xd, mdtext):
    """Best-effort pubid resolution: filename/metadata regex first, falling back
    to Copyright-header lookup via get_publication. Returns None if neither stage
    resolves a pubid."""
    pubid = find_pubid(mdtext)
    if pubid:
        return pubid
    utils.info("%s: filename did not match any known publisher, checking file headers" % mdtext)
    publ = get_publication(xd)
    if publ:
        return publ.PublicationAbbr
    return None


def deduce_xdid(xd, pubid, mdtext, strict=False):
    """Return an xdid for xd. Caller is responsible for resolving pubid (e.g. via
    resolve_pubid()). pubid may be None — strict=True returns None in that case;
    strict=False returns a provisional xdid."""
    if not pubid:
        if strict:
            return None
        return _provisional_xdid(mdtext)

    num = xd.get_header('Number')
    if num:
        return "%s-%03d" % (pubid, int(num))

    dt = xd.get_header("Date")
    if dt:
        return "%s%s" % (pubid, dt)

    if strict:
        return None
    return _provisional_xdid(mdtext, pubid=pubid)


def get_shelf_path(xd, pubid, mdtext, strict=False):
    """Return shelf path (without .xd extension). Caller is responsible for
    resolving pubid. With strict=False (default), falls through to a provisional
    path under unshelved/* when pubid or Date/Number is missing; strict=True
    returns None in those cases."""
    publ = metadb.xd_publications().get(pubid) if pubid else None

    if not publ:
        if strict:
            return None
        extsrc, _, _ = _parse_mdtext(mdtext)
        xdid = _provisional_xdid(mdtext)
        return "unshelved/%s/%s" % (extsrc or "unknown", xdid)

    publisher = publ.PublisherAbbr

    num = xd.get_header('Number')
    if num:
        return "%s/%s-%03d" % (publisher or pubid, pubid, int(num))

    dt = xd.get_header("Date")
    if dt:
        year = xdfile.year_from_date(dt)
        return "%s/%s/%s%s" % (publisher, year, pubid, dt)

    if strict:
        return None
    xdid = _provisional_xdid(mdtext, pubid=pubid)
    return "%s/unshelved/%s" % (publisher or pubid, xdid)

