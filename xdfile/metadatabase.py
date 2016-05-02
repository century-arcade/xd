
import os.path

from utils import COLUMN_SEPARATOR, EOL, parse_tsv, parse_pathname
from xdfile import corpus


RECEIPTS_TSV = "receipts.tsv"
PUBLICATIONS_TSV = "publications.tsv"
PUZZLES_TSV = "puzzles.tsv"
PUZZLE_SOURCES_TSV = "puzzle_sources.tsv"


# <source>-source-YYYY-MM-DD.zip/.tsv

# Each delivery from an extractor should have a 'sources' table, to preserve the precise external sources.
xd_sources_header = COLUMN_SEPARATOR.join([
        "SourceFilename",   # filename in the containing .zip; ideally referenceable by the ExternalSource
        "DownloadTime",     # '2016-04-11' (ISO8601; can be truncated)
        "ExternalSource",   # URL or email
    ]) + EOL


# Each row from every 'sources' table appends an expanded version to the global 'receipts' table.
xd_receipts_header = COLUMN_SEPARATOR.join([
        "ReceiptId",        # simple numeric row id (empty if Rejected)
        "DownloadTime",     # '2016-04-11' [as above, copied from xd-downloads.tsv]
        "ReceivedTime",     # '2016-04-14' [date of entry into receipts]
        "ExternalSource",   # URL or email [as above]
        "InternalSource",   # 'src/2016/xd-download-2016-04-11.zip'
        "SourceFilename",   # filename in the containing .zip [as above]
        "Rejected"          # reason for immediate rejection: obviously not a valid puzzle file; 
    ]) + EOL


# xd-publications.tsv is curated manually or via some other process
xd_publications_header = COLUMN_SEPARATOR.join([
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
xd_puzzles_header = COLUMN_SEPARATOR.join([
        "xdid",             # filename base ('nyt1994-10-02'), unique across all xd files
        "ReceiptId",        # references 'receipts' table
        "PublisherAbbr",    # 'nytimes', toplevel directory (or 'self/quigley')
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
def xd_receipts_meta(data=None):
    if not data:
        data = file(RECEIPTS_TSV, 'r').read()

    return parse_tsv(data, "Receipt")

def xd_publications_meta():
    return parse_tsv(file(PUBLICATIONS_TSV, 'r').read(), "Publication")

def xd_puzzles_meta():
    return parse_tsv(file(PUZZLES_TSV, 'r').read(), "Puzzle")

def xd_puzzles_append(tsv_rows):
    file(PUZZLES_TSV, 'a').write(tsv_rows)

def xd_puzzle_sources():
    return parse_tsv(file(PUZZLE_SOURCES_TSV, 'r').read(), "PuzzleSource")

def append_receipts(receipts):
    file(RECEIPTS_TSV, 'a').write(receipts)


def get_last_receipt_id():
    try:
        all_receipts = xd_receipts_meta()
        if all_receipts:
            return int(all_receipts[-1].ReceiptId)
        else:
            return 0
    except IOError:
        file(RECEIPTS_TSV, 'w').write(xd_receipts_header)
        return 0
        

# for each row in fnDownloadZip:*.tsv, assigns ReceiptId, ReceivedTime, and appends to receipts.tsv.  
def xd_receipts_row(nt):
    return COLUMN_SEPARATOR.join([
        str(nt.ReceiptId),
        nt.DownloadTime,
        nt.ReceivedTime,
        nt.ExternalSource,
        nt.InternalSource,
        nt.SourceFilename,
        str(nt.Rejected)
   ]) + EOL


def xd_sources_row(SourceFilename, ExternalSource, DownloadTime):
    return COLUMN_SEPARATOR.join([
        SourceFilename,
        DownloadTime,
        ExternalSource
    ]) + EOL


def xd_puzzles_row(xd, ReceiptId=""):
    fields = [
        parse_pathname(xd.filename).base,  # xdid
        str(ReceiptId),              # ReceiptId
        xd.publisher_id(),           # "nytimes"
        xd.publication_id(),         # "nyt"
        xd.get_header("Date"),
        "%dx%d %s%s" % (xd.width(), xd.height(), xd.get_header("Rebus") and "R" or "", xd.get_header("Special") and "S" or ""),

        xd.get_header("Title"),
        xd.get_header("Author") or xd.get_header("Creator"),
        xd.get_header("Editor"),
        xd.get_header("Copyright"),
        "%s_%s" % (xd.get_answer("A1"), xd.get_answer("D1"))
    ]

    assert COLUMN_SEPARATOR not in "".join(fields), fields
    return COLUMN_SEPARATOR.join(fields).encode("utf-8") + EOL

