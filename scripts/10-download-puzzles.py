#!/usr/bin/env python3

# Usage:
#  $0 -o <output-zip> <input>
#
#  Examines <input> filenames for each source and most recent date; downloads more recent puzzles and saves them to <output-zip>.
#

import urllib.request, urllib.error, urllib.parse
import datetime
import re

from xdfile.utils import get_args, log, debug, get_log, find_files, parse_pathname, open_output, parse_tsv, datestr_to_datetime
from xdfile.metadatabase import xd_sources_header, xd_sources_row, xd_puzzle_sources, xd_recent_download, xd_recent_header


def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")


def get_dates_between(before_date, after_date, days_to_advance=1):
    if before_date > after_date:
        before_date, after_date = after_date, before_date

    days_diff = (after_date - before_date).days + 1
    return [before_date + datetime.timedelta(days=x) for x in range(days_to_advance, days_diff, days_to_advance)]


def main():
    args = get_args(desc='download recent puzzles')

    outf = open_output()

    today = datetime.date.today()
    todaystr=today.strftime("%Y-%m-%d")

    sources_tsv = ''

    puzzle_sources = dict((s.PublicationAbbr, s) for s in xd_puzzle_sources())

    # download new puzzles since most recent download
    for row in parse_tsv('recents.tsv'):
        pubid = row["pubid"]
        latest_date = datestr_to_datetime(row["date"])

        if pubid not in puzzle_sources:
            log("unknown puzzle source for '%s'" % pubid)
            continue

        puzsrc = puzzle_sources[pubid]

        if not puzsrc.UrlFormat or puzsrc.UrlFormat.startswith("#"):
            log("no source url for '%s'" % pubid)
            continue


        from_date = latest_date
        to_date = today
        dates_to_get = get_dates_between(from_date, to_date, int(puzsrc.Frequency))
        if not dates_to_get:
            log("*** %s: nothing to get since %s" % (pubid, from_date))
            continue

        log("*** %s: downloading %d puzzles from %s to %s" % (pubid, len(dates_to_get), from_date, to_date))

        most_recent = {}

        for dt in dates_to_get:
            try:
                xdid = construct_xdid(pubid, dt)
                url = dt.strftime(puzsrc.UrlFormat)
                fn = "%s.%s" % (xdid, puzsrc.FileExtension)

                debug("downloading '%s' from '%s'" % (fn, url))

                response = urllib.request.urlopen(url)
                content = response.read()

                outf.write_file(fn, content)

                most_recent[pubid] = todaystr
            except (urllib.error.HTTPError, urllib.error.URLError) as err:
                log('%s [%s] %s: %s' % (xdid, err.code, err.reason, url))
            except Exception as e:
                log(str(e))

            sources_tsv += xd_sources_row(fn, url, todaystr)

    new_recents_tsv = ''
    for k, v in most_recent.items():
        new_recents_tsv += xd_recent_download(k, v)

    outf.write_file("sources.tsv", xd_sources_header + sources_tsv)
#    outf.write_file("recents.tsv", xd_recent_header + new_recents_tsv)


if __name__ == "__main__":
    main()
