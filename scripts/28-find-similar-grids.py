#!/usr/bin/env python3
"""
Find puzzle pairs with similar grid patterns, using numpy.

Reads grids from the corpus (via iter_corpus / corpus cache) and writes two
kinds of rows to similar.tsv, matching the format the legacy SQL matcher
produced (src/findmatches.sql):

  - Match rows  (xdid1, xdid2, matchpct): xdid1 is the earlier puzzle and
    matchpct is the percentage of non-block cells that share the same letter.
    A negative matchpct means the second grid matches better when transposed
    (only checked for square grids, since transposing a non-square grid
     changes its shape).
  - Sentinel rows (empty, xdid2, empty): emitted for every processed puzzle
    that never appears as xdid2 in any match — i.e., a puzzle that's been
    checked and either has no matches or only matches as the earlier puzzle.
    Disable with --no-sentinels. Puzzles deliberately skipped (e.g. redacted
    WSJ contest grids) are excluded by default; pass
    --treat-skipped-as-checked to sentinel them too.

Replaces the SQLite + C-extension matcher path
(src/findmatches.py + src/sqlite_gridcmp.c). Recomputes from scratch on every
run. For ~94k puzzles, expect roughly:
  - ~30s on a GPU via cupy
  - ~5 min on a multi-core CPU with multi-threaded BLAS
  - ~30 min on a single core
Fine for periodic local runs; probably too slow for per-commit CI without incremental
support.

Usage:
    scripts/28-find-similar-grids.py -c gxd -o gxd/similar.tsv [--threshold 30]
"""

import sys
import time
from collections import defaultdict

import numpy as np

try:
    import cupy as xp  # type: ignore[import-not-found]
    USING_GPU = True
except ImportError:
    xp = np
    USING_GPU = False

from xdfile import iter_corpus
from xdfile.utils import args_parser, get_args, info


BLOCK = ord('#')


def to_host(a):
    """Copy a cupy array back to host as numpy. No-op when running on CPU."""
    return xp.asnumpy(a) if USING_GPU else a


def grid_to_array(rows):
    """Convert a list of row strings into an (h, w) uint8 array.
    Returns None if rows are missing or have inconsistent width."""
    h = len(rows)
    if h == 0:
        return None
    w = len(rows[0])
    if any(len(r) != w for r in rows):
        return None
    arr = np.frombuffer(''.join(rows).encode('latin1', errors='replace'),
                        dtype=np.uint8)
    if arr.size != h * w:
        return None
    return arr.reshape(h, w)


def load_buckets(min_size=0, max_size=None):
    """Walk the corpus, group puzzles by grid shape (h, w). Each bucket's
    items are sorted by (date, xdid) so higher indices correspond to later
    puzzles. Grids outside [min_size, max_size] in either dimension are
    skipped (defaults: no bounds — pass --min-size to filter mini-grids)."""
    raw = defaultdict(list)
    malformed = 0
    skipped_xdids = set()
    skipped_redacted = 0
    skipped_size = 0
    for xd in iter_corpus():
        # Deliberate skip — redacted contest grids (no usable letter signal).
        if xd.is_redacted():
            xdid = xd.xdid()
            if xdid:
                skipped_xdids.add(xdid)
            skipped_redacted += 1
            continue
        arr = grid_to_array(xd.grid)
        if arr is None:
            malformed += 1
            continue
        # Deliberate skip — grid shape outside the size band.
        h, w = arr.shape
        if (h < min_size or w < min_size or
                (max_size is not None and (h > max_size or w > max_size))):
            xdid = xd.xdid()
            if xdid:
                skipped_xdids.add(xdid)
            skipped_size += 1
            continue
        date = xd.date()
        xdid = xd.xdid()
        if not date or not xdid:
            malformed += 1
            continue
        raw[arr.shape].append((xdid, date, arr))

    if malformed:
        info(f"skipped {malformed} puzzles with malformed grid or missing date/xdid")
    if skipped_redacted:
        info(f"skipped {skipped_redacted} puzzles as redacted "
             f"(e.g. WSJ/BEQ contest grids)")
    if skipped_size:
        bounds = f">={min_size}" if max_size is None else f"in [{min_size}, {max_size}]"
        info(f"skipped {skipped_size} puzzles whose shape was not {bounds}")
    if skipped_xdids:
        sample = sorted(skipped_xdids)[:5]
        more = f" ... (+{len(skipped_xdids) - len(sample)} more)" \
               if len(skipped_xdids) > len(sample) else ""
        info(f"  ({len(skipped_xdids)} unique xdids: "
             f"{', '.join(sample)}{more})")

    buckets = {}
    for key, items in raw.items():
        items.sort(key=lambda x: (x[1], x[0]))
        xdids = [x[0] for x in items]
        grids = np.stack([x[2] for x in items])
        buckets[key] = (xdids, grids)
    return buckets, skipped_xdids


def find_pairs(xdids, grids, threshold, show_progress, chunk_size=None):
    """Yield (earlier_xdid, later_xdid, matchpct) for every pair whose
    |matchpct| > threshold. `grids` must already be sorted by date ascending.

    Reframes the per-cell character comparison as an inner product on
    one-hot encoded grids: for one-hot rows `M[i]` and `M[j]`, the dot
    product `M[i] @ M[j]` counts the cells where the two grids share a
    character (since each cell contributes exactly one '1' to its row).
    The whole bucket then collapses to two matmuls per chunk, which lets
    cuBLAS or CPU BLAS do the heavy lifting."""
    if chunk_size is None:
        chunk_size = 1024 if USING_GPU else 128

    n, h, w = grids.shape
    cells = h * w
    flat = xp.asarray(grids.reshape(n, cells))

    # One-hot encode on the alphabet actually present (typically A-Z + '#').
    # M shape: (n, cells * K) float32, with `cells` ones per row.
    chars = xp.unique(flat)
    K = int(chars.size)
    M = (flat[:, :, None] == chars[None, None, :]).astype(xp.float32) \
            .reshape(n, cells * K)
    # Block-mask, used the same way to count shared-block cells.
    B = (flat == BLOCK).astype(xp.float32)

    do_transpose = (h == w)
    if do_transpose:
        flat_t = xp.asarray(grids.transpose(0, 2, 1).reshape(n, cells))
        M_T = (flat_t[:, :, None] == chars[None, None, :]).astype(xp.float32) \
                .reshape(n, cells * K)
    else:
        M_T = None

    progress_every = max(1, n // 100)
    t0 = time.time()
    last_progress = 0

    for j_start in range(0, n, chunk_size):
        j_end = min(j_start + chunk_size, n)
        chunk = j_end - j_start

        # The whole comparison: two matmuls.
        nmatches = (M[j_start:j_end] @ M.T).astype(xp.int32)   # (chunk, n)
        nblocks  = (B[j_start:j_end] @ B.T).astype(xp.int32)   # (chunk, n)
        denom = cells - nblocks
        denom_safe = xp.maximum(denom, 1)
        pct = ((nmatches - nblocks) * 100) // denom_safe

        if do_transpose:
            assert M_T is not None
            t_nmatches = (M_T[j_start:j_end] @ M.T).astype(xp.int32)
            t_pct = ((t_nmatches - nblocks) * 100) // denom_safe
            chunk_final = xp.where(t_pct > pct, -t_pct, pct)
        else:
            chunk_final = pct

        # Triangular mask: only emit pairs where haystack-index < needle-index
        j_idx = (xp.arange(chunk) + j_start)[:, None]
        i_idx = xp.arange(n)[None, :]
        keep = i_idx < j_idx
        above = (xp.abs(chunk_final) > threshold) & keep

        rows, cols = xp.nonzero(above)
        if int(rows.size) > 0:
            vals = chunk_final[rows, cols]
            rows_h = to_host(rows)
            cols_h = to_host(cols)
            vals_h = to_host(vals)
            for k, i, pct_val in zip(rows_h, cols_h, vals_h):
                yield (xdids[int(i)], xdids[j_start + int(k)], int(pct_val))

        if show_progress and (j_end - last_progress >= progress_every
                              or j_end == n):
            elapsed = time.time() - t0
            print(f"\r    {j_end}/{n} ({elapsed:.1f}s)",
                  end="", file=sys.stderr, flush=True)
            last_progress = j_end

    if show_progress:
        print(file=sys.stderr)


def main():
    p = args_parser(desc='find puzzle pairs with similar grid patterns')
    p.add_argument('--threshold', type=int, default=30,
                   help='minimum |matchpct| to emit (default: 30)')
    p.add_argument('--no-sentinels', action='store_true',
                   help='omit no-match sentinel rows for processed puzzles '
                        'that never appear as xdid2 in any match')
    p.add_argument('--treat-skipped-as-checked', action='store_true',
                   help='also emit sentinel rows for deliberately-skipped '
                        'puzzles (e.g. redacted contest grids); no effect '
                        'with --no-sentinels')
    p.add_argument('--min-size', type=int, default=0,
                   help='ignore grids with either dimension < N '
                        '(default: 0, no lower bound)')
    p.add_argument('--max-size', type=int, default=None,
                   help='ignore grids with either dimension > N '
                        '(default: unbounded)')
    args = get_args(parser=p)

    if not args.output:
        sys.exit("usage: %s -c <corpus> -o <similar.tsv>" % sys.argv[0])

    show_progress = sys.stderr.isatty()
    t_start = time.time()

    info(f"backend: {'GPU (cupy)' if USING_GPU else 'CPU (numpy)'}")
    info("loading corpus...")
    buckets, skipped_xdids = load_buckets(min_size=args.min_size,
                                          max_size=args.max_size)
    total = sum(len(xdids) for xdids, _ in buckets.values())
    info(f"loaded {total} puzzles in {len(buckets)} size buckets "
         f"({time.time()-t_start:.1f}s)")

    sorted_buckets = sorted(buckets.items(), key=lambda kv: -len(kv[1][0]))
    all_processed = {xdid for xdids, _ in buckets.values() for xdid in xdids}

    pairs = []
    for (h, w), (xdids, grids) in sorted_buckets:
        n = len(xdids)
        if n < 2:
            continue
        t0 = time.time()
        info(f"  {h}x{w}: {n} puzzles")
        bucket_pairs = list(find_pairs(xdids, grids, args.threshold,
                                       show_progress))
        pairs.extend(bucket_pairs)
        info(f"    -> {len(bucket_pairs)} pairs ({time.time()-t0:.1f}s)")

    pairs.sort(key=lambda p: (p[0], p[1]))

    if args.no_sentinels:
        sentinels = []
    else:
        # A processed puzzle that never appears as xdid2 in any match has
        # no entry yet — emit a sentinel so downstream consumers can tell
        # "checked, no matches" from "not checked".
        xdid2_set = {x2 for _, x2, _ in pairs}
        sentinel_pool = all_processed
        if args.treat_skipped_as_checked:
            sentinel_pool = sentinel_pool | skipped_xdids
        sentinels = sorted(sentinel_pool - xdid2_set)

    info(f"writing {len(pairs)} matches and {len(sentinels)} sentinels "
         f"to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("xdid1\txdid2\tmatchpct\n")
        for xdid1, xdid2, pct in pairs:
            f.write(f"{xdid1}\t{xdid2}\t{pct}\n")
        for xdid in sentinels:
            f.write(f"\t{xdid}\t\n")

    info(f"done ({time.time()-t_start:.1f}s total)")


if __name__ == '__main__':
    main()
