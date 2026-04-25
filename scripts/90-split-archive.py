#!/usr/bin/env python3
#
# Usage: $0 [-o <output-xd.zip>] [-s <source_name> ] <input>
#
#   Splits complex puzzle repos (like BWH) in <input> into separate zips
#   Default for <source_name> is input name
#


import os
import sys
import re
import time
from xdfile.utils import progress, log, iso8601, get_args, args_parser, open_output, parse_pathname
import xdfile.utils
from xdfile.metadatabase import xd_sources_row, xd_sources_header


def status(msg):
    # end any rolling progress() status cleanly, then log the summary
    if sys.stdout.isatty():
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
    log(msg)


def load_excludes(paths, files):
    excludes = set()
    for p in paths or []:
        excludes.add(p)
    for fpath in files or []:
        with open(fpath) as f:
            for i, line in enumerate(f):
                line = line.rstrip('\n')
                if not line:
                    continue
                col0 = line.split('\t', 1)[0]
                # skip a TSV header row (literal "path" in col 0)
                if i == 0 and col0 == 'path':
                    continue
                excludes.add(col0)
    return excludes


def main():
    p = args_parser('process huge puzzles archive into separate .zip and create sources.tsv')
    p.add_argument('-s', '--source', default=None, help='ExternalSource')
    p.add_argument('--exclude', action='append',
                   help='path to exclude from split (may be repeated)')
    p.add_argument('--excludes-file', action='append',
                   help='file with one path per line (or TSV; first column); may be repeated')
    p.add_argument('--min-files', type=int, default=2,
                   help='minimum number of files for a prefix to get its own zip (default: 2)')
    args = get_args(parser=p)

    open_output()

    os.makedirs(args.output, exist_ok=True)

    excludes = load_excludes(args.exclude, args.excludes_file)
    if excludes:
        status("loaded %d excluded paths" % len(excludes))

    if args.source:
        source = args.source
    else:
        source = parse_pathname(args.inputs[0]).base

    groups = {}

    t_read_start = time.monotonic()
    n_files = 0
    n_bytes = 0
    n_excluded = 0
    for inputfn in args.inputs:
        for fn, contents, dt in xdfile.utils.find_files_with_time(inputfn):
            if not contents:
                continue
            if fn in excludes:
                n_excluded += 1
                continue

            m = re.match(r'^([a-z]{2,})[-_ ]?\d', parse_pathname(fn).base, flags=re.IGNORECASE)
            prefix = m.group(1).lower() if m else 'misc'
            groups.setdefault(prefix, []).append((fn, contents, dt))
            n_files += 1
            n_bytes += len(contents)
    t_read = time.monotonic() - t_read_start
    status("READ phase: %d files, %.1f MB in %.2fs (%.0f files/s, %.1f MB/s); excluded %d" % (
        n_files, n_bytes / 1e6, t_read,
        n_files / t_read if t_read else 0,
        (n_bytes / 1e6) / t_read if t_read else 0,
        n_excluded))

    for prefix, files in list(groups.items()):
        if prefix != 'misc' and len(files) < args.min_files:
            groups.setdefault('misc', []).extend(files)
            del groups[prefix]

    t_write_start = time.monotonic()
    for prefix, files in sorted(groups.items()):
        t_zip_start = time.monotonic()
        zf = xdfile.utils.OutputZipFile(os.path.join(args.output, prefix + ".zip"))
        sources = []
        zip_bytes = 0
        for fn, contents, dt in files:
            progress("Processing %s -> %s" % (fn, prefix))
            zf.write_file(fn, contents, dt)
            sources.append(xd_sources_row(fn, source, iso8601(dt)))
            zip_bytes += len(contents)
        zf.write_file("sources.tsv", xd_sources_header + "".join(sources))
        t_zip = time.monotonic() - t_zip_start
        status("  wrote %s.zip: %d files, %.1f MB in %.2fs" % (
            prefix, len(files), zip_bytes / 1e6, t_zip))
    t_write = time.monotonic() - t_write_start
    status("WRITE phase: %d zips in %.2fs" % (len(groups), t_write))
    status("TOTAL: read=%.2fs write=%.2fs" % (t_read, t_write))


if __name__ == "__main__":
    main()
