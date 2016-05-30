
import os.path
import codecs
from collections import Counter, namedtuple

from .html import mkhref, html_select_options
from .utils import COLSEP, EOL, parse_tsv, parse_pathname
from .xdfile import corpus


RECEIPTS_TSV = "gxd/receipts.tsv"
PUBLICATIONS_TSV = "gxd/publications.tsv"
PUZZLES_TSV = "priv/puzzles.tsv"
PUZZLE_SOURCES_TSV = "gxd/sources.tsv"
RECENT_DOWNLOADS_TSV = "gxd/recents.tsv"



g_pubs = {}

# Each delivery from an extractor should have a 'sources' table, to preserve the precise external sources.
xd_sources_header = COLSEP.join([
        "ReceiptId",        # simple numeric row id (filled when approved)
        "SourceFilename",   # filename in the containing .zip; ideally referenceable by the ExternalSource
        "DownloadTime",     # '2016-04-11' (ISO8601; can be truncated)
        "ExternalSource",   # URL or email
    ]) + EOL


# Each row from every 'sources' table appends an expanded version to the global 'receipts' table.
xd_receipts_header = COLSEP.join([
        "ReceiptId",        # simple numeric row id (empty if Rejected)
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
        "ReceiptId",        # references 'receipts' table
        "PublicationAbbr",  # 'nyt', unique across all publications to support xdid format
        "Date",             # '1994-10-02'
        "Size",             # '15x15'; append 'R' for rebus
        "Title",            #
        "Author",           #
        "Editor",           #
        "Copyright",        #
        "A1_D1"             # a useful hash of the grid
    ]) + EOL


# yields dict corresponding to each row of receipts.tsv, in sequential order
def xd_receipts():
    return parse_tsv(RECEIPTS_TSV, "Receipt")

def xd_publications():
    return parse_tsv(PUBLICATIONS_TSV, "Publication")

def xd_puzzles():
    return parse_tsv(PUZZLES_TSV, "Puzzle")

def xd_puzzles_append(tsv_rows):
    codecs.open(PUZZLES_TSV, 'a', encoding='utf-8').write(tsv_rows)

def xd_puzzle_sources():
    return parse_tsv(PUZZLE_SOURCES_TSV, "PuzzleSource")

def append_receipts(receipts):
    if receipts:
        codecs.open(RECEIPTS_TSV, 'a', encoding='utf-8').write(receipts)


def get_last_receipt_id():
    try:
        all_receipts = list(xd_receipts().values())
        if all_receipts:
            return int(all_receipts[-1].ReceiptId)
        else:
            return 0
    except IOError:
        codecs.open(RECEIPTS_TSV, 'w', encoding='utf-8').write(xd_receipts_header)
        return 0
        

# for each row in fnDownloadZip:*.tsv, assigns ReceiptId, ReceivedTime, and appends to receipts.tsv.  
def xd_receipts_row(ReceiptId="", CaptureTime="", ReceivedTime="", ExternalSource="", InternalSource="", SourceFilename="", xdid=""):
    return COLSEP.join([
        str(ReceiptId),
        CaptureTime,
        ReceivedTime,
        ExternalSource,
        InternalSource,
        SourceFilename,
        xdid
    ]) + EOL


def xd_sources_row(SourceFilename, ExternalSource, DownloadTime):
    return COLSEP.join([
		"",  # ReceiptId
        SourceFilename,
        DownloadTime,
        ExternalSource
    ]) + EOL


def xd_recent_download(pubid, dt):
    return COLSEP.join([ pubid, dt ]) + EOL


def xd_puzzles_row(xd, ReceiptId=""):
    fields = [
        xd.xdid(),                   # xdid
        str(ReceiptId),              # ReceiptId
        xd.publication_id(),         # "nyt"
        xd.get_header("Date"),
        "%dx%d %s%s" % (xd.width(), xd.height(), xd.get_header("Rebus") and "R" or "", xd.get_header("Special") and "S" or ""),

        xd.get_header("Title"),
        xd.get_header("Author") or xd.get_header("Creator"),
        xd.get_header("Editor"),
        xd.get_header("Copyright"),
        "%s_%s" % (xd.get_answer("A1"), xd.get_answer("D1"))
    ]

    assert COLSEP not in "".join(fields), fields
    return COLSEP.join(fields) + EOL


def clean_copyright(puzrow):
    import re
    copyright = puzrow.Copyright
    author = puzrow.Author.strip()
    if author:
        copyright = copyright.replace(author, "&lt;Author&gt;")

    # and remove textual date
    ret = re.sub(r"\s*(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)?\s*(\d{1,2})?,?\s*\d{4},?\s*", " &lt;Date&gt; ", copyright, flags=re.IGNORECASE)

    ret = re.sub(r"\d{2}[/\-]?\d{2}[/\-]?\d{2,4}", " &lt;Date&gt; ", ret)
    return ret


class Publication:
    def __init__(self, pubid, row):
        self.publication_id = pubid
        self.row = row

class PublicationStats:
    def __init__(self, pubid):
        self.pubid = pubid
        self.copyrights = Counter()  # [copyright_text] -> number of xd
        self.editors = Counter()  # [editor_name] -> number of xd
        self.formats = Counter()  # ["15x15 RS"] -> number of xd
        self.mindate = ""
        self.maxdate = ""
        self.num_xd = 0

        self.puzzles_meta = []

    def add(self, puzrow):
        self.copyrights[clean_copyright(puzrow).strip()] += 1
        self.editors[puzrow.Editor.strip()] += 1
        self.formats[puzrow.Size] += 1
        datestr = puzrow.Date
        if datestr:
            if not self.mindate:
                self.mindate = datestr
            else:
                self.mindate = min(self.mindate, datestr)
            if not self.maxdate:
                self.maxdate = datestr
            else:
                self.maxdate = max(self.maxdate, datestr)
        self.num_xd += 1

        self.puzzles_meta.append(puzrow)

    def meta(self):
        return 'pubid num dates formats copyrights editors'.split()

    def row(self):
        return [
                self.pubid,
                mkhref(str(self.num_xd), self.pubid),
                "%s &mdash; %s" % (self.mindate, self.maxdate),
                html_select_options(self.formats),
                html_select_options(self.copyrights),
                html_select_options(self.editors),
               ]

def publications():
    if not g_pubs:
        for pubrow in xd_publications():
            pubid = pubrow.PublicationAbbr
            p = Publication(pubid, pubrow)
            g_pubs[pubid] = p

    return g_pubs


def get_publication(pubid):
    pubs = publications()
    if pubid in pubs:
        return pubs[pubid]

    p = Publication(pubid, namedtuple("Publication", xd_publications_header)(pubid, pubid, pubid, pubid, "", "", ""))
    return p
