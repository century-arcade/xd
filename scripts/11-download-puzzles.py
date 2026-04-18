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

# Per-source behavior is data-driven from gxd/sources.tsv:
#   - xword-dl_id populated -> download via xword-dl (supports date selection for most outlets)
#   - xword-dl_id empty, urlfmt populated -> download via date-templated URL
#   - both empty (or urlfmt commented with '#') -> skip

def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")

# Returns `True` if the puzzle for `date` was successfully downloaded.
def download_puzzles(outf, puzsrc, pubid, date, xwordid):
    xdid = construct_xdid(pubid, date)
    fn = "%s.%s" % (xdid, puzsrc.ext)

    if puzsrc['xword-dl_id']:
        filename_t = pubid + "%Y-%m-%d"  # wap2026-04-01
        try:
            # `content` is always a a puz.Puz object
            log("downloading '%s' using xword-dl" % (fn))
            content, filename = by_keyword(xwordid, date=date.strftime("%Y-%m-%d"), filename=filename_t)
        except Exception as e:
            try:
                log("downloading date %s using xword-dl failed; downloading latest" % date.strftime("%Y-%m-%d"))
                content, filename = by_keyword(xwordid, filename=filename_t)
            except Exception as e:
                error('xword-dl error %s: %s' % (str(e), xdid))
                return False
        if filename != fn:
            log("downloaded '%s' using xword-dl" % filename)
            fn = filename
    else:
        if not puzsrc.urlfmt or puzsrc.urlfmt.startswith("#"):
            warn("no source url for '%s', skipping" % pubid)
            return False
        url = date.strftime(puzsrc.urlfmt)
        try:
            log("downloading '%s' from url %s " % (fn, url))
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

def download_today(outf, puzzle_sources, today):
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

    if new_recents_tsv:
        # on filesystem
        open(metadb.RECENT_DOWNLOADS_TSV, "w").write(xd_recents_header + "".join(sorted(new_recents_tsv)))


MAX_CONSECUTIVE_FAILURES = 3


def download_range(outf, puzzle_sources, pubids, start, end):
    # Backfill mode: iterate pubids x dates. Does not update recent-downloads.tsv,
    # since a backfill shouldn't move the daily-cron cursor.
    for pubid in pubids:
        if pubid not in puzzle_sources:
            warn("unknown puzzle source for '%s', skipping" % pubid)
            continue

        puzsrc = puzzle_sources[pubid]
        try:
            freq = int(puzsrc.freq)
        except (ValueError, AttributeError, TypeError):
            freq = 1
        if freq < 1:
            warn("skipping '%s': invalid freq=%s" % (pubid, getattr(puzsrc, 'freq', '')))
            continue

        dt = start
        consecutive_failures = 0
        while dt <= end:
            summary("*** %s: getting puzzle for %s" % (pubid, dt))
            if download_puzzles(outf, puzsrc, pubid, dt, puzsrc['xword-dl_id']):
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    warn("'%s': %d consecutive failures, aborting range (check --start weekday alignment for freq=%d sources)" % (pubid, consecutive_failures, freq))
                    break
            time.sleep(2)
            dt += datetime.timedelta(days=freq)


def main():
    p = args_parser('download puzzles (today by default, or --start/--end range)')
    p.add_argument('--start', help='start date YYYY-MM-DD for range download')
    p.add_argument('--end', help='end date YYYY-MM-DD for range download (default: today)')
    p.add_argument('--pubid', help='limit range download to a single pubid (default: all in recent-downloads.tsv)')
    args = get_args(parser=p)
    outf = open_output()

    today = datetime.date.today()
    puzzle_sources = xd_puzzle_sources()

    if args.start or args.end:
        start = datestr_to_datetime(args.start) if args.start else today
        end = datestr_to_datetime(args.end) if args.end else today
        if args.pubid:
            pubids = [args.pubid]
        else:
            pubids = list(metadb.xd_recent_downloads().keys())
        download_range(outf, puzzle_sources, pubids, start, end)
    else:
        download_today(outf, puzzle_sources, today)

if __name__ == "__main__":
    main()
