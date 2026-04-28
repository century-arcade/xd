#!/usr/bin/env python3
"""
Find puzzle pairs with similar grid patterns, using numpy.

Reads grids from the corpus (via iter_corpus / corpus cache) and writes pairs
(xdid1, xdid2, matchpct) where xdid1 is the earlier puzzle and matchpct is
the percentage of non-block cells that share the same letter. A negative
matchpct means the second grid matches better when transposed (only checked
for 15x15 grids, matching the existing C-extension behavior in
src/sqlite_gridcmp.c).

Replaces the SQLite + C-extension matcher path
(src/findmatches.py + src/sqlite_gridcmp.c). Recomputes from scratch on every
run; for ~94k puzzles this completes in well under a minute on a single core,
so incremental bookkeeping isn't worth the complexity.

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

    # Fused per-pair kernel: one thread compares one (needle, haystack) pair,
    # counts matching cells and matching blocks in a single loop, computes
    # matchpct (and optionally t_pct for 15x15 transpose), and writes the
    # signed result. Pairs where i >= j (triangular mask) are zeroed out.
    _GRID_COMPARE_KERNEL = xp.RawKernel(r"""
extern "C" __global__
void grid_compare(
    const unsigned char* needles,
    const unsigned char* haystacks,
    int chunk_n, int chunk_h, int cells,
    int j_start, int h_start,
    int do_transpose, int rowlen,
    int* out_pct
) {
    int kk = blockIdx.x * blockDim.x + threadIdx.x;
    int ii = blockIdx.y * blockDim.y + threadIdx.y;

    if (kk >= chunk_n || ii >= chunk_h) return;

    int abs_n = j_start + kk;
    int abs_h = h_start + ii;
    int out_idx = kk * chunk_h + ii;

    if (abs_h >= abs_n) {
        out_pct[out_idx] = 0;
        return;
    }

    const unsigned char* needle = needles + kk * cells;
    const unsigned char* haystack = haystacks + ii * cells;

    int nmatches = 0;
    int nblocks = 0;
    for (int c = 0; c < cells; c++) {
        unsigned char nv = needle[c];
        unsigned char hv = haystack[c];
        if (nv == hv) {
            nmatches++;
            if (nv == 35) nblocks++;  // '#' = 35
        }
    }
    int denom = cells - nblocks;
    int pct = (denom > 0) ? ((nmatches - nblocks) * 100 / denom) : 0;

    int final_pct = pct;

    if (do_transpose) {
        int t_nmatches = 0;
        for (int c = 0; c < cells; c++) {
            int r = c / rowlen;
            int col = c % rowlen;
            int t_idx = col * rowlen + r;
            if (needle[c] == haystack[t_idx]) t_nmatches++;
        }
        int t_pct = (denom > 0) ? ((t_nmatches - nblocks) * 100 / denom) : 0;
        if (t_pct > pct) final_pct = -t_pct;
    }

    out_pct[out_idx] = final_pct;
}
""", 'grid_compare')
except ImportError:
    xp = np
    USING_GPU = False
    _GRID_COMPARE_KERNEL = None

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


def load_buckets():
    """Walk the corpus, group puzzles by grid shape (h, w). Each bucket's
    items are sorted by (date, xdid) so higher indices correspond to later
    puzzles."""
    raw = defaultdict(list)
    skipped = 0
    for xd in iter_corpus():
        arr = grid_to_array(xd.grid)
        if arr is None:
            skipped += 1
            continue
        date = xd.date()
        xdid = xd.xdid()
        if not date or not xdid:
            skipped += 1
            continue
        raw[arr.shape].append((xdid, date, arr))

    if skipped:
        info(f"skipped {skipped} puzzles (missing date/xdid or malformed grid)")

    buckets = {}
    for key, items in raw.items():
        items.sort(key=lambda x: (x[1], x[0]))
        xdids = [x[0] for x in items]
        grids = np.stack([x[2] for x in items])
        buckets[key] = (xdids, grids)
    return buckets


def find_pairs(xdids, grids, threshold, show_progress,
               needle_chunk=None, haystack_chunk=None):
    """Yield (earlier_xdid, later_xdid, matchpct) for every pair whose
    |matchpct| > threshold. `grids` must already be sorted by date ascending.

    On GPU, dispatches to a fused CUDA kernel (one thread per pair, single
    pass over both grids) — no intermediate bool arrays, no chained kernel
    launches. On CPU, falls back to chained numpy ops with smaller chunks
    tuned for L3 cache."""
    if needle_chunk is None:
        needle_chunk = 512 if USING_GPU else 64
    if haystack_chunk is None:
        haystack_chunk = 16384 if USING_GPU else 4096

    n, h, w = grids.shape
    cells = h * w
    flat = xp.asarray(grids.reshape(n, cells))

    do_transpose = (h == 15 and w == 15)

    # CPU path needs precomputed block masks and a transposed copy.
    # GPU kernel handles both inline per-pair.
    if USING_GPU:
        flat_is_block = None
        flat_t = None
    else:
        flat_is_block = (flat == BLOCK)
        flat_t = (xp.asarray(grids.transpose(0, 2, 1).reshape(n, cells))
                  if do_transpose else None)

    progress_every = max(1, n // 100)
    t0 = time.time()
    last_progress = 0

    for j_start in range(1, n, needle_chunk):
        j_end = min(j_start + needle_chunk, n)
        chunk_size = j_end - j_start

        needles = flat[j_start:j_end]
        needles_block = None
        needles_t = None
        if not USING_GPU:
            assert flat_is_block is not None
            needles_block = flat_is_block[j_start:j_end]
            if do_transpose:
                assert flat_t is not None
                needles_t = flat_t[j_start:j_end]

        for h_start in range(0, j_end, haystack_chunk):
            h_end = min(h_start + haystack_chunk, j_end)
            h_chunk_size = h_end - h_start
            haystack = flat[h_start:h_end]

            if USING_GPU:
                # One kernel launch, one pass over data.
                assert _GRID_COMPARE_KERNEL is not None
                chunk_final = xp.empty((chunk_size, h_chunk_size),
                                       dtype=xp.int32)
                block_dim = (32, 8, 1)
                grid_dim = (
                    (chunk_size + block_dim[0] - 1) // block_dim[0],
                    (h_chunk_size + block_dim[1] - 1) // block_dim[1],
                    1,
                )
                _GRID_COMPARE_KERNEL(grid_dim, block_dim, (
                    needles, haystack,
                    np.int32(chunk_size), np.int32(h_chunk_size),
                    np.int32(cells),
                    np.int32(j_start), np.int32(h_start),
                    np.int32(1 if do_transpose else 0), np.int32(w),
                    chunk_final,
                ))
                # Kernel already zeroed invalid pairs (i >= j); threshold filter
                # below naturally excludes them since |0| < threshold.
                above = xp.abs(chunk_final) > threshold
            else:
                assert flat_is_block is not None
                assert needles_block is not None
                haystack_block = flat_is_block[h_start:h_end]

                eq = (haystack[None, :, :] == needles[:, None, :])
                nmatches = eq.sum(axis=2)
                both_block = haystack_block[None, :, :] & needles_block[:, None, :]
                nblocks = both_block.sum(axis=2)
                denom = cells - nblocks
                denom_safe = xp.maximum(denom, 1)
                valid = denom > 0

                chunk_pct = (((nmatches - nblocks) * 100) // denom_safe).astype(xp.int32)
                chunk_pct = xp.where(valid, chunk_pct, xp.int32(0))

                if do_transpose:
                    assert needles_t is not None
                    eq_t = (haystack[None, :, :] == needles_t[:, None, :])
                    t_nmatches = eq_t.sum(axis=2)
                    chunk_t_pct = (((t_nmatches - nblocks) * 100) // denom_safe).astype(xp.int32)
                    chunk_t_pct = xp.where(valid, chunk_t_pct, xp.int32(0))
                    chunk_final = xp.where(chunk_t_pct > chunk_pct,
                                           -chunk_t_pct, chunk_pct)
                else:
                    chunk_final = chunk_pct

                j_idx = (xp.arange(chunk_size) + j_start)[:, None]
                i_idx = xp.arange(h_start, h_end)[None, :]
                keep = i_idx < j_idx
                above = (xp.abs(chunk_final) > threshold) & keep

            rows, cols = xp.nonzero(above)
            if int(rows.size) > 0:
                vals = chunk_final[rows, cols]
                rows_h = to_host(rows)
                cols_h = to_host(cols)
                vals_h = to_host(vals)
                for k, ci, pct_val in zip(rows_h, cols_h, vals_h):
                    yield (xdids[h_start + int(ci)],
                           xdids[j_start + int(k)],
                           int(pct_val))

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
    args = get_args(parser=p)

    if not args.output:
        sys.exit("usage: %s -c <corpus> -o <similar.tsv>" % sys.argv[0])

    show_progress = sys.stderr.isatty()
    t_start = time.time()

    info(f"backend: {'GPU (cupy)' if USING_GPU else 'CPU (numpy)'}")
    info("loading corpus...")
    buckets = load_buckets()
    total = sum(len(xdids) for xdids, _ in buckets.values())
    info(f"loaded {total} puzzles in {len(buckets)} size buckets "
         f"({time.time()-t_start:.1f}s)")

    sorted_buckets = sorted(buckets.items(), key=lambda kv: -len(kv[1][0]))

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

    info(f"writing {len(pairs)} pairs to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("xdid1\txdid2\tmatchpct\n")
        for xdid1, xdid2, pct in pairs:
            f.write(f"{xdid1}\t{xdid2}\t{pct}\n")

    info(f"done ({time.time()-t_start:.1f}s total)")


if __name__ == '__main__':
    main()
