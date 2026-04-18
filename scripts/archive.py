#!/usr/bin/env python3
"""
General-purpose xword-dl archive/backfill script.

Downloads puzzles for any xword-dl source between a start and end date,
saving .puz files into per-source subdirectories under ./archive/.

Resumable: skips any puzzle that already has a .puz file on disk.

Usage:
    python archive.py COMMAND --start YYYY-MM-DD [--end YYYY-MM-DD] [--interval daily|monthly]
                               [--delay-min 0.5] [--delay-max 1.5] [--output DIR]

Examples:
    python archive.py nytbonus --start 1997-02-01 --interval monthly
    python archive.py nytm    --start 2014-08-21
    python archive.py nytmid  --start 2026-02-25
    python archive.py atl     --start 2020-01-01 --end 2024-12-31
    python archive.py nyt     --start 2000-01-01 --delay-min 2 --delay-max 5
"""

import argparse
import os
import random
import time
from datetime import date, datetime, timedelta

from xword_dl.downloader import get_plugins
from xword_dl.util import save_puzzle

ARCHIVE_ROOT = os.path.join(os.path.dirname(__file__), "archive")

CONSECUTIVE_ERROR_THRESHOLD = 5
LONG_PAUSE = 120


def generate_dates(start, end, interval):
    current = start
    while current <= end:
        yield current
        if interval == "daily":
            current += timedelta(days=1)
        elif interval == "monthly":
            month = current.month % 12 + 1
            year = current.year + (1 if current.month == 12 else 0)
            current = current.replace(year=year, month=month)


def get_downloader_class(command):
    plugins = get_plugins()
    for plugin in plugins:
        if getattr(plugin, "command", None) == command:
            return plugin
    return None


def list_available():
    plugins = get_plugins()
    sources = sorted(
        [(p.command, p.outlet) for p in plugins if p.command],
        key=lambda x: x[1].lower(),
    )
    print("Available sources:")
    for cmd, outlet in sources:
        print(f"  {cmd:<10} {outlet}")


def run(args):
    cls = get_downloader_class(args.command)
    if cls is None:
        print(f"Unknown command: {args.command}")
        print()
        list_available()
        return 1

    out_dir = os.path.join(args.output, args.command)
    os.makedirs(out_dir, exist_ok=True)

    end = args.end or date.today()
    dates = list(generate_dates(args.start, end, args.interval))
    total = len(dates)

    print(f"\n{'='*60}")
    print(f"{cls.outlet} ({args.command}) | {total} puzzles | "
          f"{args.start} to {end} ({args.interval})")
    print(f"Output: {out_dir}")
    print(f"Delay: {args.delay_min}-{args.delay_max}s")
    print(f"{'='*60}")

    dl = cls()

    downloaded = 0
    skipped = 0
    errors = 0
    consecutive_errors = 0

    for i, dt in enumerate(dates, 1):
        date_str = dt.strftime("%Y-%m-%d")

        existing = [
            f for f in os.listdir(out_dir)
            if date_str.replace("-", "") in f and f.endswith(".puz")
        ]
        if existing:
            skipped += 1
            continue

        print(f"[{i}/{total}] {args.command} {date_str} ... ", end="", flush=True)

        try:
            dl.date = dt
            puzzle_url = dl.find_by_date(dt)
            puzzle = dl.download(puzzle_url)
            filename = dl.pick_filename(puzzle)
            filepath = os.path.join(out_dir, filename)
            save_puzzle(puzzle, filepath)
            downloaded += 1
            consecutive_errors = 0
            print("OK")
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break
        except Exception as e:
            errors += 1
            consecutive_errors += 1
            print(f"FAILED: {e}")

            if consecutive_errors >= CONSECUTIVE_ERROR_THRESHOLD:
                print(f"  {consecutive_errors} consecutive errors, "
                      f"pausing {LONG_PAUSE}s ...")
                time.sleep(LONG_PAUSE)
                consecutive_errors = 0

        delay = random.uniform(args.delay_min, args.delay_max)
        time.sleep(delay)

    print(f"\n{args.command} complete: {downloaded} downloaded, "
          f"{skipped} skipped, {errors} errors")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Backfill/archive puzzles from any xword-dl source.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with --list to see all available sources.",
    )
    parser.add_argument("command", nargs="?", help="xword-dl source command (e.g. nyt, nytm, atl)")
    parser.add_argument("--start", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        default=None, help="End date (YYYY-MM-DD, default: today)")
    parser.add_argument("--interval", choices=["daily", "monthly"], default="daily",
                        help="Date step interval (default: daily)")
    parser.add_argument("--delay-min", type=float, default=0.5,
                        help="Minimum delay between requests in seconds (default: 0.5)")
    parser.add_argument("--delay-max", type=float, default=1.5,
                        help="Maximum delay between requests in seconds (default: 1.5)")
    parser.add_argument("--output", default=ARCHIVE_ROOT,
                        help=f"Output root directory (default: {ARCHIVE_ROOT})")
    parser.add_argument("--list", action="store_true", help="List available sources and exit")

    args = parser.parse_args()

    if args.list or not args.command:
        list_available()
        return

    if not args.start:
        parser.error("--start is required")

    run(args)


if __name__ == "__main__":
    main()
