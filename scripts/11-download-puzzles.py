#!/usr/bin/env python3

# Usage:
#  $0 -o <output-zip> -r <recent-downloads.tsv>
#
#  Examines <input> filenames for each source and most recent date; downloads more recent puzzles and saves them to <output-zip>.
#
#  <output-zip> is a gxd source archive (see gxd's CONTRIBUTING.md): the puzzles at its root,
#  plus MANIFEST.tsv (sha256, size, source URL, fetch time per file), NOTES.md and the run log.
#

import urllib.request
import urllib.error
import urllib.parse
import puz
import datetime
import os
import sys
import time

from xdfile import metadatabase as metadb
from xdfile import utils
from xdfile.utils import get_args, log, error, warn, summary, datestr_to_datetime, args_parser, get_log, OutputZipFile
from xdfile.sourcearchive import SourceArchiveWriter, git_commit, package_version
from xdfile.metadatabase import xd_puzzle_sources, xd_recent_download, xd_recents_header

from xword_dl import by_keyword


def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")

# Returns `True` if the puzzle for `date` was successfully downloaded.
# `arc` is a SourceArchiveWriter; it records each attempt and each saved file.
def download_puzzles(arc, puzsrc, pubid, date, xwordid, fallback_latest=True):
    xdid = construct_xdid(pubid, date)
    fn = "%s.%s" % (xdid, puzsrc.ext)
    # Only the urlfmt path has the publisher's bytes and URL; xword-dl returns its own
    # .puz rendering of the publisher's data, so those files get no source_url.
    source_url = ''

    if puzsrc['xword-dl_id']:
        filename_t = pubid + "%Y-%m-%d"  # wap2026-04-01
        try:
            # `content` is always a a puz.Puz object
            log("%s: fetching via xword-dl" % xdid)
            content, filename = by_keyword(xwordid, date=date.strftime("%Y-%m-%d"), filename=filename_t)
        except Exception as e:
            if not fallback_latest:
                error("%s: xword-dl failed: %s" % (xdid, e))
                arc.attempt(pubid, date, "failed", "xword-dl: %s" % e)
                return False
            log("%s: xword-dl fetch failed (%s); retrying for latest issue" % (xdid, e))
            try:
                content, filename = by_keyword(xwordid, filename=filename_t)
            except Exception as e2:
                error("%s: xword-dl gave up: %s" % (xdid, e2))
                arc.attempt(pubid, date, "failed", "xword-dl: %s; latest issue: %s" % (e, e2))
                return False
        if filename != fn:
            log("%s: got '%s' instead of requested date" % (xdid, filename))
            fn = filename
    else:
        if not puzsrc.urlfmt or puzsrc.urlfmt.startswith("#"):
            warn("%s: no source url, skipping" % pubid)
            arc.attempt(pubid, date, "skipped", "no xword-dl_id or urlfmt in sources.tsv")
            return False
        url = date.strftime(puzsrc.urlfmt)
        try:
            log("%s: fetching from %s" % (xdid, url))
            # Type of `content` depends on the publication
            response = urllib.request.urlopen(url, timeout=10)
            content = response.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            error("%s: %s: %s" % (xdid, err, url))
            arc.attempt(pubid, date, "failed", "%s: %s" % (url, err))
            return False
        source_url = url

    if isinstance(content, puz.Puzzle):
        content = content.tobytes()
    arc.add_file(fn, content, pubid=pubid, requested_date=date, source_url=source_url)
    if fn == "%s.%s" % (xdid, puzsrc.ext):
        arc.attempt(pubid, date, "saved", fn)
    else:
        arc.attempt(pubid, date, "saved", "%s (latest issue, not the requested date)" % fn)
    summary("%s: saved %s (%d bytes)" % (xdid, fn, len(content)))
    return True

def download_today(arc, puzzle_sources, today, only_pubids=None, sleep_ms=2000):
    new_recents_tsv = []
    # Some downloads may fail, track the last successful ones
    most_recent = {}

    # For each publication, download today's puzzle if we don't already have it
    for row in metadb.xd_recent_downloads().values():
        pubid = row.pubid
        if only_pubids and pubid not in only_pubids:
            continue
        if pubid not in puzzle_sources:
            warn("unknown puzzle source for '%s', skipping" % pubid)
            arc.attempt(pubid, '', 'skipped', 'not in sources.tsv')
            continue

        # If download fails, retain the most recent download date
        latest_date = datestr_to_datetime(row.date)
        most_recent[pubid] = row.date
        if latest_date == today:
            continue

        puzsrc = puzzle_sources[pubid]

        summary("*** %s: getting puzzle for %s" % (pubid, today))
        if download_puzzles(arc, puzsrc, pubid, today, puzzle_sources[pubid]['xword-dl_id']):
            most_recent[pubid] = today.strftime("%Y-%m-%d")

        # Might not need this sleep since each iteration is a different url
        time.sleep(sleep_ms / 1000)

    for k, v in most_recent.items():
        new_recents_tsv.append(xd_recent_download(k, v))

    if new_recents_tsv:
        # on filesystem
        open(metadb.RECENT_DOWNLOADS_TSV, "w").write(xd_recents_header + "".join(sorted(new_recents_tsv)))


def download_range(arc, puzzle_sources, pubids, start, end, sleep_ms=2000, max_consecutive_failures=3):
    # Backfill mode: iterate pubids x dates. Does not update recent-downloads.tsv,
    # since a backfill shouldn't move the daily-cron cursor.
    for pubid in pubids:
        if pubid not in puzzle_sources:
            warn("unknown puzzle source for '%s', skipping" % pubid)
            arc.attempt(pubid, '', 'skipped', 'not in sources.tsv')
            continue

        puzsrc = puzzle_sources[pubid]
        try:
            freq = int(puzsrc.freq)
        except (ValueError, AttributeError, TypeError):
            freq = 1
        if freq < 1:
            warn("skipping '%s': invalid freq=%s" % (pubid, getattr(puzsrc, 'freq', '')))
            arc.attempt(pubid, '', 'skipped', 'invalid freq=%s' % getattr(puzsrc, 'freq', ''))
            continue

        dt = start
        consecutive_failures = 0
        while dt <= end:
            summary("*** %s: getting puzzle for %s" % (pubid, dt))
            if download_puzzles(arc, puzsrc, pubid, dt, puzsrc['xword-dl_id'], fallback_latest=False):
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    warn("'%s': %d consecutive failures, aborting range (check --start weekday alignment for freq=%d sources)" % (pubid, consecutive_failures, freq))
                    if dt < end:
                        arc.attempt(pubid, '%s..%s' % (dt + datetime.timedelta(days=freq), end), 'skipped',
                                    '%d consecutive failures, rest of range not attempted' % consecutive_failures)
                    break
            time.sleep(sleep_ms / 1000)
            dt += datetime.timedelta(days=freq)


def main():
    p = args_parser('download puzzles (today by default, or --start/--end range)')
    p.add_argument('--start', help='start date YYYY-MM-DD for range download')
    p.add_argument('--end', help='end date YYYY-MM-DD for range download (default: today)')
    p.add_argument('--pubid', nargs='+', help='limit download to one or more pubids (default: all in recent-downloads.tsv)')
    p.add_argument('--sleep-ms', type=int, default=2000, help='delay between downloads in milliseconds (default: 2000)')
    p.add_argument('--max-consecutive-failures', type=int, default=3, help='abort a pubid in range mode after this many consecutive failed downloads (default: 3)')
    args = get_args(parser=p)
    if not args.output or not args.output.endswith(".zip"):
        p.error("-o/--output must be a .zip (e.g. -o puzzles.zip)")

    # No top-level folder in the zip: each puzzle's path in the archive is the
    # SourceFilename that 18-convert2xd.py records, as gxd's MANIFEST.tsv requires.
    # The log is written by arc.finish() (so it can be listed in the manifest),
    # not by OutputZipFile on close.
    outf = OutputZipFile(args.output, toplevel="", log=False)
    arc = SourceArchiveWriter(outf, utils.g_scriptname)

    today = datetime.date.today()
    puzzle_sources = xd_puzzle_sources()

    try:
        if args.start or args.end:
            start = datestr_to_datetime(args.start) if args.start else today
            end = datestr_to_datetime(args.end) if args.end else today
            pubids = args.pubid if args.pubid else list(metadb.xd_recent_downloads().keys())
            download_range(arc, puzzle_sources, pubids, start, end,
                           sleep_ms=args.sleep_ms,
                           max_consecutive_failures=args.max_consecutive_failures)
        else:
            download_today(arc, puzzle_sources, today, only_pubids=args.pubid)
    finally:
        xddir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        arc.finish(get_log(),
                   command=" ".join([os.path.basename(sys.argv[0])] + sys.argv[1:]),
                   xd_commit=git_commit(xddir),
                   xworddl_version=package_version("xword-dl"))
        outf.close()

if __name__ == "__main__":
    main()
