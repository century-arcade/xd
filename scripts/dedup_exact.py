#!/usr/bin/env python3
"""Find and optionally delete byte-identical suffixed xd files.

Scans for pairs where xdid+suffix (e.g. nyt2014-10-12a.xd) is byte-identical
to xdid (e.g. nyt2014-10-12.xd). By default, does a dry run listing what would
be deleted. Pass --delete to actually remove files.
"""

import argparse
import os
import re
import sys


def find_xd_files(path):
    """Walk directory and return dict of xdid -> filepath."""
    xdids = {}
    for dirpath, dirnames, filenames in os.walk(path):
        for fn in filenames:
            if fn.endswith(".xd"):
                xdid = fn[:-3]  # strip .xd
                xdids[xdid] = os.path.join(dirpath, fn).replace("\\", "/")
    return xdids


def find_suffix_pairs(xdids):
    """Find (base_xdid, suffixed_xdid) pairs where suffixed = base + letter suffix."""
    pairs = []
    for xdid in xdids:
        # match date-based xdids with a suffix after the date
        m = re.match(r'(.+\d{4}-\d{2}-\d{2})(.+)$', xdid)
        if not m:
            continue
        base = m.group(1)
        suffix = m.group(2)
        if base in xdids:
            pairs.append((base, xdid, suffix))
    return sorted(pairs)


def main():
    parser = argparse.ArgumentParser(
        description="Find and remove byte-identical suffixed xd duplicates"
    )
    parser.add_argument("path", help="Path to gxd directory")
    parser.add_argument("--delete", action="store_true",
                        help="Actually delete files (default is dry run)")
    args = parser.parse_args()

    print(f"Scanning {args.path}...", file=sys.stderr)
    xdids = find_xd_files(args.path)
    print(f"Found {len(xdids)} xd files", file=sys.stderr)

    pairs = find_suffix_pairs(xdids)
    print(f"Found {len(pairs)} suffixed pairs to check", file=sys.stderr)
    print(file=sys.stderr)

    byte_identical = []
    differ = []

    for base, suffixed, suffix in pairs:
        base_path = xdids[base]
        suf_path = xdids[suffixed]

        with open(base_path, "rb") as f:
            base_bytes = f.read()
        with open(suf_path, "rb") as f:
            suf_bytes = f.read()

        if base_bytes == suf_bytes:
            byte_identical.append((base, suffixed, suf_path))
        else:
            differ.append((base, suffixed))

    print(f"Byte-identical pairs: {len(byte_identical)}", file=sys.stderr)
    print(f"Pairs with differences: {len(differ)}", file=sys.stderr)
    print(file=sys.stderr)

    if not byte_identical:
        print("Nothing to delete.", file=sys.stderr)
        return

    if args.delete:
        for base, suffixed, suf_path in byte_identical:
            print(f"DELETE {suffixed} (dup of {base}): {suf_path}")
            os.remove(suf_path)
        print(f"\nDeleted {len(byte_identical)} files.", file=sys.stderr)
    else:
        for base, suffixed, suf_path in byte_identical:
            print(f"WOULD DELETE {suffixed} (dup of {base}): {suf_path}")
        print(f"\nDry run: {len(byte_identical)} files would be deleted. "
              f"Pass --delete to remove them.", file=sys.stderr)


if __name__ == "__main__":
    main()
