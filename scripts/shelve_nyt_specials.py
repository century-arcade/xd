#!/usr/bin/env python3
"""One-off script to rename unshelved nyt-XXXX monthly bonus puzzles
to proper date-based xdids (nytYYYY-MM-00) and update receipts.tsv."""

import os
import re
import sys


def parse_number_to_date(number_str):
    """Convert Number header (YYMM with possible missing leading zeros) to (yyyy, mm)."""
    padded = number_str.zfill(4)
    yy = int(padded[:2])
    mm = int(padded[2:])
    if mm < 1 or mm > 12:
        return None
    yyyy = 1900 + yy if yy >= 50 else 2000 + yy
    return yyyy, mm


def main():
    gxd = "gxd"
    dry_run = "--dry-run" in sys.argv

    # find all unshelved nyt-*.xd files
    nyt_dir = os.path.join(gxd, "nytimes")
    files = sorted(f for f in os.listdir(nyt_dir) if re.match(r'nyt-\d+\.xd$', f))

    if not files:
        print("No nyt-*.xd files found.", file=sys.stderr)
        return

    print(f"Found {len(files)} unshelved files.", file=sys.stderr)

    renames = []  # (old_xdid, new_xdid, old_path, new_path)
    errors = []

    for fn in files:
        old_path = os.path.join(nyt_dir, fn)
        old_xdid = fn[:-3]  # strip .xd

        # read Number header
        number = None
        with open(old_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    break
                if line.startswith("Number:"):
                    number = line.split(":", 1)[1].strip()
                    break

        if not number:
            errors.append(f"{fn}: no Number header")
            continue

        result = parse_number_to_date(number)
        if not result:
            errors.append(f"{fn}: bad Number '{number}'")
            continue

        yyyy, mm = result
        new_xdid = f"nyt{yyyy}-{mm:02d}-00"
        new_dir = os.path.join(nyt_dir, str(yyyy))
        new_path = os.path.join(new_dir, new_xdid + ".xd")

        if os.path.exists(new_path):
            errors.append(f"{fn}: target already exists: {new_path}")
            continue

        # validate against Copyright year if present
        with open(old_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    break
                if line.startswith("Copyright:"):
                    m = re.search(r'(\d{4})', line)
                    if m and int(m.group(1)) != yyyy:
                        errors.append(f"{fn}: Number→{yyyy} but Copyright says {m.group(1)}")
                    break

        renames.append((old_xdid, new_xdid, old_path, new_path, new_dir))

    # show plan
    for old_xdid, new_xdid, old_path, new_path, new_dir in renames:
        print(f"{old_xdid} -> {new_xdid}")

    if errors:
        print(f"\nErrors ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)

    if dry_run:
        print(f"\nDry run: {len(renames)} renames. Pass without --dry-run to execute.", file=sys.stderr)
        return

    # move files
    for old_xdid, new_xdid, old_path, new_path, new_dir in renames:
        os.makedirs(new_dir, exist_ok=True)
        os.rename(old_path, new_path)

    # update receipts.tsv: only update the most recent row per xdid
    receipts_path = os.path.join(gxd, "receipts.tsv")
    xdid_map = {old: new for old, new, _, _, _ in renames}

    with open(receipts_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # find the last occurrence of each old xdid (most recent receipt)
    last_line_for_xdid = {}
    for i, line in enumerate(lines):
        fields = line.rstrip("\n").split("\t")
        if len(fields) >= 6 and fields[5] in xdid_map:
            last_line_for_xdid[fields[5]] = i

    updated = 0
    deleted = 0
    new_lines = []
    for i, line in enumerate(lines):
        fields = line.rstrip("\n").split("\t")
        if len(fields) >= 6 and fields[5] in xdid_map:
            if i == last_line_for_xdid[fields[5]]:
                # rename the most recent row
                fields[5] = xdid_map[fields[5]]
                updated += 1
                new_lines.append("\t".join(fields) + "\n")
            elif len(fields) >= 5 and fields[4].endswith("sp.puz"):
                # delete older orphaned rows, but only sp.puz sources
                deleted += 1
            else:
                # keep non-sp.puz rows (buick, delta, etc.)
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(receipts_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"\nMoved {len(renames)} files, updated {updated} receipt rows, deleted {deleted} old rows.", file=sys.stderr)


if __name__ == "__main__":
    main()
