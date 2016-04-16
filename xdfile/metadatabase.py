
from utils import COLUMN_SEPARATOR, EOL
from xdfile import corpus


# <source>-source-YYYY-MM-DD.zip/.tsv

# Each delivery from an extractor should have a 'sources' table, to preserve the precise external sources.
xd_sources_header = COLUMN_SEPARATOR.join([
        "SourceFilename",   # filename in the containing .zip; ideally referenceable by the ExternalSource
        "DownloadTime",     # '2016-04-11T01:24' [ISO8601]
        "ExternalSource",   # URL or email
    ]) + EOL


# Each row from every 'sources' table appends an expanded version to the global 'receipts' table.
xd_receipts_header = COLUMN_SEPARATOR.join([
        "ReceiptId",        # simple numeric row id (empty if Rejected)
        "DownloadTime",     # [these identically-named fields copied from above xd-downloads.tsv]
        "ReceivedTime",     # '2016-04-14'; any Date or Time can be truncated
        "ExternalSource",   # [see above]
        "InternalSource",   # 'src/2016/xd-download-2016-04-11.zip'
        "SourceFilename",   # [see above]
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
        "1-Across/1-Down"   # a useful hash of the grid
    ]) + EOL


# yields dict corresponding to each row of receipts.tsv, in sequential order
def receipts_meta():
    return parse_tsv(file(RECEIPTS_TSV, 'r').read())

def publications_meta():
    return parse_tsv(file(PUBLICATIONS_TSV, 'r').read())

def puzzles_meta():
    return parse_tsv(file(PUZZLES_TSV, 'r').read())

def append_receipts(receipts):
    file(RECEIPTS_TSV, 'a').write(receipts)

# for each row in fnDownloadZip:*.tsv, assigns ReceiptId, ReceivedTime, and appends to receipts.tsv.  
def xd_receipts_row(nt):
    return COLUMN_SEPARATOR.join([
        nt.ReceiptId,
        nt.DownloadTime,
        nt.ReceivedTime,
        nt.ExternalSource,
        nt.InternalSource,
        nt.SourceFilename,
        nt.Rejected
   ]) + EOL

# for each row in fnDownloadZip:*.tsv, converts to .xd and appends to puzzles.tsv
def convert_sources(fnDownloadZip):
    abbrid, d = parse_date_from_filename(xd.filename)
    pubid = xd.filename.split("/")[1]

    yearstr = d and str(d.year) or ""
    datestr = d and d.strftime("%Y-%m-%d") or ""

    fields = [
        parse_fn(xd.filename).base,
        xd.source,
        pubid,
        abbrid + yearstr,
        xd.get_header("Date") or datestr,
        "%dx%d" % xd.size(),
        xd.get_header("Title"),
        xd.get_header("Author"),
        xd.get_header("Editor"),
        "%s/%s" % (xd.get_answer("A1"), xd.get_answer("D1"))
    ]

    assert SEP not in "".join(fields), fields
    return COLUMN_SEPARATOR.join(fields).encode("utf-8")


def xd_source_row(SourceFilename, ExternalSource, DownloadTime):
    return COLUMN_SEPARATOR.join([
        SourceFilename,
        DownloadTime,
        ExternalSource
    ]) + EOL

