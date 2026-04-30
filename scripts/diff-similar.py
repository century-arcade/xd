#!/usr/bin/env python3
"""
Summarize the diff between two versions of gxd/similar.tsv.

similar.tsv has two row types — they're independent, not grouped:
  - Match rows have all three columns:   xdid1  xdid2  matchpct
  - "Processed, no matches" sentinel rows have empty xdid1 and empty
    matchpct, with just xdid2 populated. The legacy SQL matcher emits
    one of these for any puzzle that has been checked but never appears
    as xdid2 in a real match (see src/findmatches.sql).

The metadatabase parser in xdfile/metadatabase.py skips sentinel rows
(`if r.matchpct: ...`); they're a bookkeeping artifact, not pair data.

This script diffs the two files independently for both row types, and
canonicalizes match pairs so (A,B) and (B,A) compare equal.

Usage:
    summarize-similar-diff.py                       # working copy vs HEAD (default)
    summarize-similar-diff.py REV                   # working copy vs REV
    summarize-similar-diff.py OLD_PATH NEW_PATH     # diff two files on disk
    summarize-similar-diff.py --git [REV_OLD [REV_NEW]]   # rev vs rev (default HEAD~1 vs HEAD)

The default behavior matches `git diff`: with no args, compare HEAD against
the working-copy file at --file. With a single positional, that's treated
as the OLD rev and the working copy is NEW. With two positionals, both are
treated as file paths.

Git modes read from `git show` in the cwd. Run from inside the target repo
(cd gxd && python ../scripts/summarize-similar-diff.py), or pass -C DIR to
have the script cd there for you (python scripts/summarize-similar-diff.py
-C gxd, from xd/).
"""

import argparse
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict


# xdids come in two flavors: <pubid><date> (e.g. nyt2024-01-15) and
# <pubid>-<id> (e.g. beq-219, slate-BREASTPOCKET). Pubids may start with
# a digit (e.g. 7xw). The pubid is matched non-greedily so the date or
# hyphen-separator is consumed by the rest of the pattern.
XDID_RE = re.compile(r"^([a-z0-9]+?)(?:\d{4}-\d{2}-\d{2}|-.+)$")


def parse_rows(text):
    """Parse similar.tsv into (pairs, sentinels, malformed_count).
       pairs: dict (xdid_a, xdid_b) -> matchpct, canonicalized xdid_a < xdid_b
       sentinels: set of xdids that appear as bare-xdid2 rows
                  ("processed, no matches as xdid2")"""
    pairs = {}
    sentinels = set()
    malformed = 0

    lines = text.splitlines()
    start = 1 if lines and lines[0].startswith("xdid1") else 0

    for raw in lines[start:]:
        if not raw.strip():
            continue
        cols = raw.split("\t")
        while len(cols) < 3:
            cols.append("")
        xdid1, xdid2, pct = cols[0], cols[1], cols[2]

        if xdid1 and xdid2 and pct:
            try:
                pct_i = int(pct)
            except ValueError:
                malformed += 1
                continue
            a, b = sorted((xdid1, xdid2))
            pairs[(a, b)] = pct_i
        elif not xdid1 and xdid2 and not pct:
            sentinels.add(xdid2)
        else:
            malformed += 1

    return pairs, sentinels, malformed


def pub_of(xdid):
    m = XDID_RE.match(xdid)
    return m.group(1) if m else "?"


def bucket_of(pct):
    p = abs(pct)
    if p == 100:
        return "100"
    if p >= 90:
        return "90-99"
    if p >= 75:
        return "75-89"
    if p >= 50:
        return "50-74"
    if p >= 30:
        return "30-49"
    return "<30"


BUCKETS = ["100", "90-99", "75-89", "50-74", "30-49", "<30"]


def read_git(rev_path):
    """rev_path like 'HEAD~1:similar.tsv'; cwd is repo root."""
    out = subprocess.run(
        ["git", "show", rev_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        sys.exit(f"git show {rev_path} failed: {out.stderr.strip()}")
    return out.stdout


def read_path(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def fmt_pct(n, total):
    return f"{n:>7}  ({100.0 * n / total:5.1f}%)" if total else f"{n:>7}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--git", action="store_true",
                    help="rev-vs-rev mode (default REV_OLD=HEAD~1, REV_NEW=HEAD)")
    ap.add_argument("--file", default="similar.tsv",
                    help="path within the repo when using git mode "
                         "(default: similar.tsv)")
    ap.add_argument("-C", "--directory",
                    help="cd to DIR before running (mirrors `git -C`); "
                         "lets you invoke from outside the target repo")
    ap.add_argument("--sample", type=int, default=10,
                    help="how many sample entries to show per section (default: 10)")
    args = ap.parse_args()

    # Mode selection — matches `git diff` defaults: no args = working copy vs
    # HEAD, one positional = working copy vs that rev, two positional = paths.
    if args.git:
        mode = "git"
    elif args.old and args.new:
        mode = "paths"
    else:
        mode = "worktree"

    # If chdir'ing, resolve positional path args first so relative paths
    # resolve from the user's original cwd.
    if args.directory:
        if mode == "paths":
            args.old = os.path.abspath(args.old)
            args.new = os.path.abspath(args.new)
        os.chdir(args.directory)

    if mode == "worktree":
        old_rev = args.old or "HEAD"
        old_label = f"{old_rev}:{args.file}"
        new_label = f"{args.file} (working copy)"
        old_text = read_git(old_label)
        new_text = read_path(args.file)
    elif mode == "git":
        old_rev = args.old or "HEAD~1"
        new_rev = args.new or "HEAD"
        old_label = f"{old_rev}:{args.file}"
        new_label = f"{new_rev}:{args.file}"
        old_text = read_git(old_label)
        new_text = read_git(new_label)
    else:  # paths
        old_label, new_label = args.old, args.new
        old_text = read_path(args.old)
        new_text = read_path(args.new)

    old_pairs, old_sent, old_bad = parse_rows(old_text)
    new_pairs, new_sent, new_bad = parse_rows(new_text)

    old_keys = set(old_pairs)
    new_keys = set(new_pairs)
    added = new_keys - old_keys
    removed = old_keys - new_keys
    common = old_keys & new_keys
    changed = {k for k in common if old_pairs[k] != new_pairs[k]}

    sent_added = new_sent - old_sent
    sent_removed = old_sent - new_sent

    print(f"similar.tsv diff summary")
    print(f"=========================")
    print(f"OLD: {old_label}")
    print(f"     {len(old_text.splitlines()):>7} lines  "
          f"{len(old_pairs):>6} match rows  {len(old_sent):>6} sentinel rows"
          + (f"  ({old_bad} malformed)" if old_bad else ""))
    print(f"NEW: {new_label}")
    print(f"     {len(new_text.splitlines()):>7} lines  "
          f"{len(new_pairs):>6} match rows  {len(new_sent):>6} sentinel rows"
          + (f"  ({new_bad} malformed)" if new_bad else ""))
    print()

    total_changes = len(added) + len(removed) + len(changed)
    print(f"Match-row changes")
    print(f"-----------------")
    print(f"  added       {fmt_pct(len(added),   total_changes)}")
    print(f"  removed     {fmt_pct(len(removed), total_changes)}")
    print(f"  pct changed {fmt_pct(len(changed), total_changes)}")
    print(f"  unchanged   {len(common) - len(changed):>7}")
    print(f"  net matches {len(new_pairs) - len(old_pairs):+d}")
    print()

    print(f"Sentinel-row changes")
    print(f"--------------------")
    print(f"  added         {len(sent_added):>7}")
    print(f"  removed       {len(sent_removed):>7}")
    print(f"  net sentinels {len(new_sent) - len(old_sent):+d}")
    if sent_added:
        print(f"  sample added:   {sorted(sent_added)[:args.sample]}")
    if sent_removed:
        print(f"  sample removed: {sorted(sent_removed)[:args.sample]}")
    print()

    # Bucket distribution for added/removed/pct-changed
    def bucket_counts(keys, source):
        c = Counter(bucket_of(source[k]) for k in keys)
        return c

    add_b = bucket_counts(added, new_pairs)
    rem_b = bucket_counts(removed, old_pairs)
    print(f"By matchpct bucket")
    print(f"------------------")
    print(f"  bucket   added  removed")
    for b in BUCKETS:
        if add_b[b] or rem_b[b]:
            print(f"  {b:>6}  {add_b[b]:>6}  {rem_b[b]:>7}")
    print()

    # Per-publisher breakdown (each pair counted twice — once per side).
    pub_add = Counter()
    pub_rem = Counter()
    for a, b in added:
        pub_add[pub_of(a)] += 1
        pub_add[pub_of(b)] += 1
    for a, b in removed:
        pub_rem[pub_of(a)] += 1
        pub_rem[pub_of(b)] += 1

    pubs = sorted(set(pub_add) | set(pub_rem),
                  key=lambda p: -(pub_add[p] + pub_rem[p]))
    print(f"By publisher (each pair counted on both sides)")
    print(f"----------------------------------------------")
    print(f"  pub      added  removed     net")
    for p in pubs[:20]:
        net = pub_add[p] - pub_rem[p]
        print(f"  {p:<6}  {pub_add[p]:>6}  {pub_rem[p]:>7}  {net:+7d}")
    if len(pubs) > 20:
        print(f"  ... +{len(pubs)-20} more publishers")
    print()

    # xdids appearing/disappearing entirely.
    old_xdids = {x for k in old_keys for x in k}
    new_xdids = {x for k in new_keys for x in k}
    only_new = new_xdids - old_xdids
    only_old = old_xdids - new_xdids

    print(f"xdids by membership")
    print(f"-------------------")
    print(f"  in OLD only:   {len(only_old):>6}")
    print(f"  in NEW only:   {len(only_new):>6}")
    print(f"  in both:       {len(old_xdids & new_xdids):>6}")
    if only_new:
        print(f"  sample (NEW only): {sorted(only_new)[:args.sample]}")
    if only_old:
        print(f"  sample (OLD only): {sorted(only_old)[:args.sample]}")
    print()

    # Per-xdid match-count delta — which puzzles gained/lost the most matches.
    old_deg = Counter()
    new_deg = Counter()
    for a, b in old_keys:
        old_deg[a] += 1
        old_deg[b] += 1
    for a, b in new_keys:
        new_deg[a] += 1
        new_deg[b] += 1

    deltas = []
    for xdid in old_xdids | new_xdids:
        d = new_deg[xdid] - old_deg[xdid]
        if d:
            deltas.append((xdid, old_deg[xdid], new_deg[xdid], d))

    gainers = sorted(deltas, key=lambda r: -r[3])[:args.sample]
    losers  = sorted(deltas, key=lambda r:  r[3])[:args.sample]

    print(f"Largest match-count gains per xdid")
    print(f"----------------------------------")
    print(f"  xdid                  old    new    delta")
    for xdid, o, n, d in gainers:
        print(f"  {xdid:<20} {o:>5}  {n:>5}  {d:+6d}")
    print()

    if losers and losers[0][3] < 0:
        print(f"Largest match-count losses per xdid")
        print(f"-----------------------------------")
        print(f"  xdid                  old    new    delta")
        for xdid, o, n, d in losers:
            if d >= 0:
                break
            print(f"  {xdid:<20} {o:>5}  {n:>5}  {d:+6d}")
        print()

    # Sample of changed pcts — what got reweighted?
    if changed:
        print(f"matchpct changes (sample)")
        print(f"-------------------------")
        print(f"  xdid1                xdid2                  old -> new")
        sample_changed = sorted(changed,
                                key=lambda k: -abs(new_pairs[k] - old_pairs[k]))
        for k in sample_changed[:args.sample]:
            a, b = k
            print(f"  {a:<20} {b:<20} {old_pairs[k]:>4} -> {new_pairs[k]:>4}")
        print()

    # Sample additions, split into perfect matches (which usually dominate
    # and are uninteresting once you've seen one or two) and the top
    # near-but-not-100% matches, which are where the algorithmic edge cases
    # live.
    def print_sample(title, pairs_set, source, key):
        if not pairs_set:
            return
        print(title)
        print("-" * len(title))
        for k in sorted(pairs_set, key=key)[:args.sample]:
            a, b = k
            print(f"  {a:<20} {b:<20} {source[k]:>4}")
        print()

    if added:
        added_100 = {k for k in added if abs(new_pairs[k]) == 100}
        added_sub = added - added_100
        print_sample("Sample added pairs at 100%",
                     added_100, new_pairs, key=lambda k: (k[0], k[1]))
        print_sample("Sample added pairs <100% (highest first)",
                     added_sub, new_pairs, key=lambda k: -abs(new_pairs[k]))

    if removed:
        removed_100 = {k for k in removed if abs(old_pairs[k]) == 100}
        removed_sub = removed - removed_100
        print_sample("Sample removed pairs at 100%",
                     removed_100, old_pairs, key=lambda k: (k[0], k[1]))
        print_sample("Sample removed pairs <100% (highest first)",
                     removed_sub, old_pairs, key=lambda k: -abs(old_pairs[k]))


if __name__ == "__main__":
    main()
