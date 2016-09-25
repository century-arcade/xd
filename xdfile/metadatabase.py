
import os.path
import codecs
import fnmatch
from collections import Counter, namedtuple

from .html import mkhref, html_select_options
from .utils import COLSEP, EOL
from .xdfile import corpus

from xdfile import utils


RECEIPTS_TSV = "gxd/receipts.tsv"
SIMILAR_TSV = "gxd/similar.tsv"
PUBLICATIONS_TSV = "gxd/publications.tsv"
PUZZLE_SOURCES_TSV = "gxd/sources.tsv"
RECENT_DOWNLOADS_TSV = "gxd/recent-downloads.tsv"
STATS_TSV = "pub/stats.tsv"


class Error(Exception):
    pass


# Each delivery from an extractor should have a 'sources' table, to preserve the precise external sources.
xd_sources_header = COLSEP.join([
        "ReceiptId",        # simple numeric row id (filled when approved)
        "SourceFilename",   # filename in the containing .zip; ideally referenceable by the ExternalSource
        "DownloadTime",     # '2016-04-11' (ISO8601; can be truncated)
        "ExternalSource",   # URL or email
    ]) + EOL


# Each row from every 'sources' table appends an expanded version to the global 'receipts' table.
xd_receipts_header = COLSEP.join([
        "CaptureTime",     # '2016-04-11' [as above, copied from xd-downloads.tsv]
        "ReceivedTime",     # '2016-04-14' [date of entry into receipts]
        "ExternalSource",   # URL or email [as above]
        "InternalSource",   # 'src/2016/xd-download-2016-04-11.zip'
        "SourceFilename",   # filename in the containing .zip [as above]
        "xdid"              # Shelf location (check log for error if empty)
    ]) + EOL


# Each delivery from an extractor should have a 'sources' table, to preserve the precise external sources.
xd_recents_header = COLSEP.join([
        "pubid",
        "date",
    ]) + EOL


# xd-publications.tsv is curated manually or via some other process
xd_publications_header = COLSEP.join([
        "PublicationAbbr",  # 'nyt', should be unique across all publications; same as xdid prefix
        "PublisherAbbr",    # 'nytimes', toplevel directory (or 'self/quigley', or 'misc')
        "PublicationName",  # 'The New York Times'
        "PublisherName",    # 'New York Times Publishing Company'
        "FirstIssueDate",   # YYYY-MM-DD; empty if unknown
        "LastIssueDate",    # YYYY-MM-DD; empty if ongoing
        "NumberIssued",     # estimates allowed with leading '~'
    ]) + EOL

# xd-puzzles.tsv
# if ReceiptId's are preserved, generating a sorted list from all .xd files should result in an identical .tsv file.
xd_puzzles_header = COLSEP.join([
        "xdid",             # filename base ('nyt1994-10-02'), unique across all xd files
        "Date",             # '1994-10-02'
        "Size",             # '15x15'; append 'R' for rebus, 'S' for shaded squares
        "Title",            #
        "Author",           #
        "Editor",           #
        "Copyright",        #
        "A1_D1"             # a useful hash of the grid
    ]) + EOL

xd_stats_header = COLSEP.join([
    "pubid",
    "year",
    "weekday",
    "Size",
    "Editor",
    "Copyright",
    "NumExisting",
    "NumXd",
    "NumPublic",
    "NumReprints",
    "NumTouchups",
    "NumRedone",
    "NumSuspicious",
    "NumThemeCopies",
])


xddb_headers = {
    'pub/stats': xd_stats_header,
    'pub/puzzles': xd_puzzles_header,
    'gxd/similar': 'xdid similar_grid_pct reused_clues reused_answers total_clues matches',
    'gxd/publications': xd_publications_header,
    'gxd/recents': xd_recents_header,
    'gxd/receipts': xd_receipts_header,
    'gxd/sources': xd_sources_header,
}


# yields dict corresponding to each row of receipts.tsv, in sequential order
@utils.memoize
def xd_receipts():
    return utils.parse_tsv(RECEIPTS_TSV, "Receipt")


@utils.memoize
def xd_receipts_rows():
    return utils.parse_tsv_rows(RECEIPTS_TSV, "Receipt")


@utils.memoize
def xd_publications():
    return dict((r.PublicationAbbr, r) for r in read_rows('gxd/publications'))


def xd_puzzle(xdid):
    return xd_puzzles_dict().get(xdid)


@utils.memoize
def xd_puzzles_dict():
    return dict((p.xdid, p) for p in _puzzles())


def xd_puzzles(xdid=''):
    if not xdid:
        return _puzzles()

    return [p for p in _puzzles() if p.xdid.startswith(xdid)]


def get_author(xdid=''):
    r = xd_puzzles(xdid)
    return str(r[0].Author) if r else "???"


@utils.memoize
def _puzzles():
    return utils.parse_tsv_rows('pub/puzzles.tsv', "Puzzle")


@utils.memoize
def xd_puzzle_sources():
    return dict((r.pubid, r) for r in utils.parse_tsv_rows(PUZZLE_SOURCES_TSV))


@utils.memoize
def xd_recent_downloads():
    return dict((r.pubid, r) for r in utils.parse_tsv_rows(RECENT_DOWNLOADS_TSV))


def delete_stats():
    try:
        os.remove(STATS_TSV)
    except:
        pass


def stats():
    return utils.parse_tsv(STATS_TSV, "Stat")


def read_rows(tablename):
    tsvpath = tablename + ".tsv"
    basename = tablename.split('/')[-1]
    return utils.parse_tsv_rows(tsvpath, basename)


def append_row(tablename, row):
    tsvpath = tablename + ".tsv"
    addhdr = not os.path.exists(tsvpath)

    fp = codecs.open(tsvpath, 'a', encoding='utf-8')
    if addhdr:
        fp.write(COLSEP.join(xddb_headers[tablename].split()) + EOL)

    fp.write(COLSEP.join([str(x) for x in row]) + EOL)
    fp.close()


def get_last_receipt_id():
    try:
        all_receipts = list(xd_receipts().values())
        if all_receipts:
            return max(int(r.ReceiptId) for r in all_receipts)
        else:
            return 0
    except IOError:
        codecs.open(RECEIPTS_TSV, 'w', encoding='utf-8').write(xd_receipts_header)
        return 0


# for each row in fnDownloadZip:*.tsv, assigns ReceiptId, ReceivedTime, and appends to receipts.tsv.
def xd_receipts_row(CaptureTime="", ReceivedTime="", ExternalSource="", InternalSource="", SourceFilename="", xdid=""):
    return COLSEP.join([
        CaptureTime,
        ReceivedTime,
        ExternalSource,
        InternalSource,
        SourceFilename,
        xdid
    ]) + EOL


def check_already_received(ExternalSource, SourceFilename):
    ret = []
    for r in read_rows('gxd/receipts'):
        if r.ExternalSource == ExternalSource and r.SourceFilename == SourceFilename:
            ret.append(r)
    return ret


def xd_sources_row(SourceFilename, ExternalSource, DownloadTime):
    return COLSEP.join([
        "",  # ReceiptId
        SourceFilename,
        DownloadTime,
        ExternalSource
    ]) + EOL


def xd_recent_download(pubid, dt):
    return COLSEP.join([ pubid, dt ]) + EOL


def update_puzzles_row(xd):
    # INSERT only for now
    if xd.xdid() in xd_puzzles():
        raise Error('record already exists; UPDATE not implemented')

    fields = [
        xd.xdid(),                   # xdid
        xd.get_header("Date"),
        "%dx%d%s%s" % (xd.width(), xd.height(), xd.get_header("Rebus") and "R" or "", xd.get_header("Special") and "S" or ""),

        xd.get_header("Title"),
        xd.get_header("Author") or xd.get_header("Creator"),
        xd.get_header("Editor"),
        xd.get_header("Copyright"),
        "%s_%s" % (xd.get_answer("A1"), xd.get_answer("D1"))
    ]

    assert COLSEP not in "".join(fields), fields

    append_row("pub/puzzles", fields)


xd_similar_tuple = namedtuple("GridMatch", "xdid match_xdid match_pct")


@utils.memoize
def xd_similar(xdid=''):
    ret = []

    for r in xd_similar_all():
        if r.xdid.startswith(xdid):
            ret.append(r)
        if r.match_xdid.startswith(xdid):
            # swap xdid and xdidMatch
            ret.append(xd_similar_tuple(r.match_xdid, r.xdid, r.match_pct))

    return ret


@utils.memoize
def xd_similar_all():
    ''' returns a list of all similar grids '''

    ret = []
    for r in utils.parse_tsv_rows('gxd/similar.tsv', 'Similar'):
        matches = [x.split('=') for x in r.matches.split()]
        for match_xdid, pct in matches:
            ret.append(xd_similar_tuple(r.xdid, match_xdid, int(pct)))

    return ret


@utils.memoize
def public_patterns():
    return codecs.open('gxd/public.txt', 'r', encoding='utf-8').read().splitlines()


def is_public(xdid):
    for pattern in public_patterns():
        if fnmatch.fnmatch(xdid, str(pattern)):
            return True

    return False
