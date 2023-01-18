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
import re
import json
import base64

from xdfile import utils, metadatabase as metadb
from xdfile.utils import get_args, log, error, warn, summary, debug, open_output, datestr_to_datetime, args_parser
from xdfile.metadatabase import xd_sources_header, xd_sources_row, xd_puzzle_sources, xd_recent_download, xd_recents_header


def construct_xdid(pubabbr, dt):
    return pubabbr + dt.strftime("%Y-%m-%d")


def get_dates_between(before_date, after_date, days_to_advance=1):
    if before_date > after_date:
        before_date, after_date = after_date, before_date

    days_diff = (after_date - before_date).days
    return [before_date + datetime.timedelta(days=x) for x in range(0, days_diff, days_to_advance)]


def add_days(dt, ndays):
    return dt + datetime.timedelta(days=ndays)

def get_ungotten_dates(pubid, before_date, after_date, days_to_advance, ret=None):
    def prev_period(start_date, period=days_to_advance):
        return add_days(start_date, -period*2)

    if ret is None:
        ret = []

    newret = []
    pub_gotten = set()
    for puzrow in metadb.xd_puzzles(pubid):
        pub_gotten.add(datestr_to_datetime(puzrow.Date))

    if before_date > after_date:
        before_date, after_date = after_date, before_date

    before_before_date = prev_period(before_date)

    days_diff = (after_date - before_before_date).days

    for offset in range(days_to_advance, days_diff+1, days_to_advance):
        dt = add_days(before_before_date, offset)
        if dt not in pub_gotten:
            newret.append(dt)

    ret.extend(reversed(newret))

    if newret:
        return get_ungotten_dates(pubid, prev_period(before_before_date), before_before_date, days_to_advance, ret)
    else:
        return ret


def main():
    p = args_parser('download recent puzzles')
    args = get_args(parser=p)

    outf = open_output()

    today = datetime.date.today()
    sources_tsv = ''

    puzzle_sources = xd_puzzle_sources()

    new_recents_tsv = []

    # some downloads may fail, track the last successful ones
    most_recent = {}

    # download new puzzles since most recent download
    for row in metadb.xd_recent_downloads().values():
        pubid = row.pubid
        latest_date = datestr_to_datetime(row.date)

        # by default, keep the previous one
        most_recent[pubid] = row.date

        if pubid not in puzzle_sources:
            warn("unknown puzzle source for '%s', skipping" % pubid)
            continue

        puzsrc = puzzle_sources[pubid]

        if not puzsrc.urlfmt or puzsrc.urlfmt.startswith("#"):
            warn("no source url for '%s', skipping" % pubid)
            continue

        summary("*** %s: getting puzzles for %s" % (pubid, today))
        dates_to_get = [today]
        most_recent[pubid] = str(download_puzzles(outf, puzsrc, pubid, list(set(dates_to_get))))

    #for k, v in most_recent.items():
    #    new_recents_tsv.append(xd_recent_download(k, v))

#    if sources_tsv:
#        outf.write_file("sources.tsv", xd_sources_header + sources_tsv)

    #if new_recents_tsv:
        # on filesystem
     #   open(metadb.RECENT_DOWNLOADS_TSV, "w").write(xd_recents_header + "".join(sorted(new_recents_tsv)))


# returns most recent date actually gotten
def download_puzzles(outf, puzsrc, pubid, dates_to_get):
    from xword_dl import by_keyword
    actually_gotten = []

    # AmuseLabs query urls require a pickerToken
    xworddl_outlets = ['lat']

    for dt in sorted(dates_to_get):
        try:
            xdid = construct_xdid(pubid, dt)
            url = dt.strftime(puzsrc.urlfmt)
            fn = "%s.%s" % (xdid, puzsrc.ext)

            debug("downloading '%s' from '%s'" % (fn, url))

            if pubid in xworddl_outlets:
                # content is a puz.Puz object
                content, filename = by_keyword(pubid, date=dt.strftime("%Y-%m-%d"))

            else:
                response = urllib.request.urlopen(url, timeout=10)
                content = response.read()

            if isinstance(content, puz.Puzzle):
                content = content.tobytes()
            outf.write_file(fn, content)
            actually_gotten.append(dt)
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            error('%s %s: %s' % (xdid, err, url))
        except Exception as e:
            raise e

#        sources_tsv += xd_sources_row(fn, url, todaystr)
        time.sleep(2)

    return max(actually_gotten) if actually_gotten else 0


if __name__ == "__main__":
    main()
