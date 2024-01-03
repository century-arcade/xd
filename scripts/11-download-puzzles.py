#!/usr/bin/env python3

# Usage:
#  $0 -o <output-zip> -r <recent-downloads.tsv>
#
#  Examines <input> filenames for each source and most recent date; downloads more recent puzzles and saves them to <output-zip>.
#

import urllib.request, urllib.error, urllib.parse
import puz
import datetime
import time
import json

from xdfile import utils, metadatabase as metadb
from xdfile.utils import get_args, log, error, warn, summary, debug, open_output, datestr_to_datetime, args_parser
from xdfile.metadatabase import xd_sources_header, xd_sources_row, xd_puzzle_sources, xd_recent_download, xd_recents_header

from xword_dl import by_keyword

# For supported outlets, use xword-dl to download a .puz file of the most recent puzzle.
# this is the xd pubid
XWORDDL_OUTLETS = ['lat', 'tny', 'up', 'usa', 'nw', 'atl', 'nyt']
# wsj, wap do not support selection by date
# wap is not a daily but does have its pub date in the 'copyright'
# field of the .puz
# wsj frequency is unknown, .puz does not seem to include a pub date
# we need to add a check on which date got downloaded

def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")

# Returns `True` if the puzzle for `date` was successfully downloaded.
def download_puzzles(outf, puzsrc, pubid, date, xwordid):
    xdid = construct_xdid(pubid, date)
    url = date.strftime(puzsrc.urlfmt)
    fn = "%s.%s" % (xdid, puzsrc.ext)

    if pubid in XWORDDL_OUTLETS:
        try:
            # `content` is always a a puz.Puz object
            log("downloading '%s' using xword-dl" % (fn))
            content, filename = by_keyword(xwordid, date=date.strftime("%Y-%m-%d"))
        except Exception as e:
            try:
                log("downloading date %s using xword-dl failed; downloading latest" % date.strftime("%Y-%m-%d"))
                content, filename = by_keyword(xwordid)
            except Exception as e:
                error('xword-dl error %s: %s' % (str(e), xdid))
                return False
    else:
        try:
            log("downloading '%s' from url %s " % (fn, url))
            if not url or url.startswith("#"):
                warn("no source url for '%s', skipping" % pubid)
                return False
            # Type of `content` depends on the publication
            response = urllib.request.urlopen(url, timeout=10)
            content = response.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            error('%s %s: %s' % (xdid, err, url))
            return False

    if isinstance(content, puz.Puzzle):
        content = content.tobytes()
    outf.write_file(fn, content)
    return True

def main():
    p = args_parser('download today\'s puzzles')
    args = get_args(parser=p)
    outf = open_output()

    today = datetime.date.today()
    sources_tsv = ''
    puzzle_sources = xd_puzzle_sources()
    new_recents_tsv = []

    # Some downloads may fail, track the last successful ones
    most_recent = {}

    # For each publication, download today's puzzle if we don't already have it
    for row in metadb.xd_recent_downloads().values():
        pubid = row.pubid
        if pubid not in puzzle_sources:
            warn("unknown puzzle source for '%s', skipping" % pubid)
            continue

        # If download fails, retain the most recent download date
        latest_date = datestr_to_datetime(row.date)
        most_recent[pubid] = row.date
        if latest_date == today:
            continue

        puzsrc = puzzle_sources[pubid]

        summary("*** %s: getting puzzle for %s" % (pubid, today))
        if download_puzzles(outf, puzsrc, pubid, today, puzzle_sources[pubid]['xword-dl_id']):
            most_recent[pubid] = today.strftime("%Y-%m-%d")

        # Might not need this sleep since each iteration is a different url
        time.sleep(2)

    for k, v in most_recent.items():
        new_recents_tsv.append(xd_recent_download(k, v))

    if sources_tsv:
        outf.write_file("sources.tsv", xd_sources_header + sources_tsv)

    if new_recents_tsv:
        # on filesystem
        open(metadb.RECENT_DOWNLOADS_TSV, "w").write(xd_recents_header + "".join(sorted(new_recents_tsv)))

if __name__ == "__main__":
    main()
