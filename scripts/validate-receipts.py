#!/usr/bin/env python3
"""
validate-receipts.py — GitLab CI check for gxd/.

Invariants checked against the diff between --base and --head:

  1. Every newly-added receipts.tsv row with a non-empty xdid belongs to an
     (ExternalSource, SourceFilename) key for which *some* xdid in receipts at --head
     has a matching *.xd file in the tree. This tolerates pure modifications and
     stale-row rewrites: as long as the key still maps to an existing .xd via any
     of its receipts, the row passes.
  2. Every newly-added *.xd file has a receipts.tsv row at --head whose xdid column
     matches the file's basename.
  3. Every deleted *.xd file is OK to remove: its xdid is NOT the latest non-empty
     xdid (by ReceivedTime) for any (ExternalSource, SourceFilename) key. Stale
     orphan deletions pass; deletions of currently-authoritative files fail.

The check validates the tree state at --head, not the diff itself — so a back-fill
(a new receipts row for a file added in a prior commit, or vice versa) passes.

Requires no working-tree checkout; uses `git ls-tree` and `git show` against the
--head sha. Runs fine with GIT_STRATEGY=fetch.
"""
import argparse
import os
import re
import subprocess
import sys


# 0-indexed columns: CaptureTime, ReceivedTime, ExternalSource, InternalSource, SourceFilename, xdid
CAPTURE_COL = 0
RECEIVED_COL = 1
EXT_COL = 2
INT_COL = 3
SRC_COL = 4
XDID_COL = 5
NCOLS = 6

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
XDID_RE = re.compile(r"^[a-z0-9._-]+$")


def git(*args):
    return subprocess.check_output(["git", *args], text=True)


def iter_added_rows(base, head, receipts):
    """Yield (raw_body, fields) for every `+` line in the receipts diff, skipping the
    header row. `raw_body` is the line without the leading `+`; `fields` is the
    tab-split column list (untrimmed)."""
    diff = git("diff", "--unified=0", "--no-color", f"{base}..{head}", "--", receipts)
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        fields = body.split("\t")
        if len(fields) > XDID_COL and fields[XDID_COL].strip() == "xdid":
            continue  # header line
        yield body, fields


def check_row_format(fields):
    """Return list of human-readable problems with `fields` as a receipts.tsv row.
    Empty list means well-formed. Empty xdid is allowed (rejected/unfinished puzzles);
    every other column must be non-empty, and dates/xdid must match expected shape."""
    if len(fields) != NCOLS:
        return [f"expected {NCOLS} tab-separated columns, got {len(fields)}"]
    capture, received, ext, internal, src, xdid = (f.strip() for f in fields)
    problems = []
    if not DATE_RE.match(capture):
        problems.append(f"CaptureTime not YYYY-MM-DD: {capture!r}")
    if not DATE_RE.match(received):
        problems.append(f"ReceivedTime not YYYY-MM-DD: {received!r}")
    if not ext:
        problems.append("ExternalSource is empty")
    if not internal:
        problems.append("InternalSource is empty")
    if not src:
        problems.append("SourceFilename is empty")
    if xdid and not XDID_RE.match(xdid):
        problems.append(f"xdid has unexpected characters: {xdid!r}")
    return problems


def added_receipts_rows(base, head, receipts):
    """(ExternalSource, SourceFilename, xdid) tuples for `+` rows in the receipts diff.
    Skips short/malformed rows — those are reported separately by check_row_format."""
    rows = []
    for _body, fields in iter_added_rows(base, head, receipts):
        if len(fields) <= XDID_COL:
            continue
        rows.append((fields[EXT_COL], fields[SRC_COL], fields[XDID_COL].strip()))
    return rows


def added_xd_paths(base, head):
    """Paths of *.xd files added in this diff."""
    out = git("diff", "--name-only", "--diff-filter=A", f"{base}..{head}")
    return [p for p in out.splitlines() if p.endswith(".xd")]


def deleted_xd_paths(base, head):
    """Paths of *.xd files deleted in this diff."""
    out = git("diff", "--name-only", "--diff-filter=D", f"{base}..{head}")
    return [p for p in out.splitlines() if p.endswith(".xd")]


def receipts_latest_xdids(head, receipts):
    """Set of xdids that are the latest non-empty xdid (by ReceivedTime) for some
    (ExternalSource, SourceFilename) key in receipts at head. These are the xdids
    actively claimed by receipts; deleting their .xd files would create a dangling claim.
    """
    out = git("show", f"{head}:{receipts}")
    by_key = {}
    for i, line in enumerate(out.splitlines()):
        if i == 0:
            continue
        fields = line.split("\t")
        if len(fields) <= XDID_COL:
            continue
        key = (fields[EXT_COL], fields[SRC_COL])
        by_key.setdefault(key, []).append((fields[RECEIVED_COL], fields[XDID_COL]))
    latest = set()
    for rows in by_key.values():
        non_empty = [(r, x) for r, x in rows if x]
        if non_empty:
            latest.add(max(non_empty, key=lambda t: t[0])[1])
    return latest


def tree_xdids(head):
    """Set of xdids present in the head tree (basename of every *.xd file)."""
    out = git("ls-tree", "-r", "--name-only", head)
    return {os.path.basename(p)[:-3] for p in out.splitlines() if p.endswith(".xd")}


def receipts_xdids_by_key(head, receipts):
    """{(ExternalSource, SourceFilename): set(xdids)} from receipts at head."""
    out = git("show", f"{head}:{receipts}")
    by_key = {}
    for i, line in enumerate(out.splitlines()):
        if i == 0:
            continue
        fields = line.split("\t")
        if len(fields) <= XDID_COL:
            continue
        key = (fields[EXT_COL], fields[SRC_COL])
        by_key.setdefault(key, set()).add(fields[XDID_COL])
    return by_key


def receipts_xdids(head, receipts):
    """Set of non-empty xdids in the receipts file at head."""
    by_key = receipts_xdids_by_key(head, receipts)
    return {x for xdids in by_key.values() for x in xdids if x}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="Diff base ref/sha (e.g. MR base or prior HEAD)")
    ap.add_argument("--head", default="HEAD", help="Diff head ref/sha (default: HEAD)")
    ap.add_argument("--receipts", default="receipts.tsv", help="Path to receipts TSV (default: receipts.tsv)")
    args = ap.parse_args()

    errors = []

    new_rows = added_receipts_rows(args.base, args.head, args.receipts)
    new_xd_paths = added_xd_paths(args.base, args.head)
    deleted_xds = deleted_xd_paths(args.base, args.head)

    for body, fields in iter_added_rows(args.base, args.head, args.receipts):
        problems = check_row_format(fields)
        if problems:
            preview = body if len(body) <= 100 else body[:97] + "..."
            for p in problems:
                errors.append(f"{args.receipts}: malformed row [{preview}]: {p}")

    rows_with_xdid = [r for r in new_rows if r[2]]
    if rows_with_xdid:
        tree = tree_xdids(args.head)
        by_key = receipts_xdids_by_key(args.head, args.receipts)
        seen_keys = set()
        for ext_src, src_fn, xdid in rows_with_xdid:
            key = (ext_src, src_fn)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            key_xdids = by_key.get(key, set())
            if not any(x and x in tree for x in key_xdids):
                errors.append(
                    f"{args.receipts}: ({ext_src!r}, {src_fn!r}): none of the xdids "
                    f"for this key ({sorted(x for x in key_xdids if x)!r}) has a matching .xd file in the tree"
                )

    if new_xd_paths:
        receipts = receipts_xdids(args.head, args.receipts)
        for path in new_xd_paths:
            xdid = os.path.basename(path)[:-3]
            if xdid not in receipts:
                errors.append(
                    f"{path} was added but no {args.receipts} row has xdid {xdid!r}"
                )

    if deleted_xds:
        latest_xdids = receipts_latest_xdids(args.head, args.receipts)
        for path in deleted_xds:
            xdid = os.path.basename(path)[:-3]
            if xdid in latest_xdids:
                errors.append(
                    f"{path} was deleted but xdid {xdid!r} is still the latest authoritative "
                    f"xdid for some (ExternalSource, SourceFilename) key in {args.receipts}"
                )

    if errors:
        print("receipts/shelf validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    summary = f"OK ({len(new_rows)} new receipts row(s), {len(new_xd_paths)} new .xd file(s), {len(deleted_xds)} deleted .xd file(s))"
    print(summary)


if __name__ == "__main__":
    main()
