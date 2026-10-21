"""Reproducible stratified samples of the corpus (e.g. held-out eval sets).

Selection rule:
  1. Filter: drop redacted puzzles, puzzles outside [since, before), and
     anything listed in an exclude file (e.g. an earlier sample).
  2. Per-publication quota: round(N / rate), floored at min_per_pub and
     capped at N, where N is the publication's count after filtering.
  3. Within each publication, the quota is split across decades in
     proportion to the decade counts (largest-remainder; ties go to the
     later decade).
  4. Within each (publication, decade) stratum, candidates are shuffled
     with an RNG seeded from (seed, pubid, decade) and taken in order,
     skipping any whose grid is >= max_similar percent similar to a
     puzzle already chosen or excluded (reprints, syndication copies).

No filtering on content (rebus, themes, size): puzzles appear at their
natural rate. Seeding per stratum means adding puzzles to one publication
does not change the draw for any other publication.
"""

import random
from collections import defaultdict, namedtuple


Candidate = namedtuple('Candidate', 'xdid pubid date')


def decade_of(date):
    try:
        return (int(date[:4]) // 10) * 10
    except (TypeError, ValueError):
        return None


def in_window(date, since=None, before=None):
    """date, since, before are ISO strings (YYYY-MM-DD, may be truncated)."""
    if not date:
        return since is None and before is None
    if since and date < since:
        return False
    if before and date >= before:
        return False
    return True


def quota(n, rate, min_per_pub):
    return min(n, max(min_per_pub, int(n / rate + 0.5)))


def split_by_decade(k, decade_counts):
    """Largest-remainder split of k across decades, proportional to counts."""
    total = sum(decade_counts.values())
    if k <= 0 or total == 0:
        return {d: 0 for d in decade_counts}
    exact = {d: k * c / total for d, c in decade_counts.items()}
    alloc = {d: int(x) for d, x in exact.items()}
    leftover = k - sum(alloc.values())
    # biggest remainder first; ties to the later decade (None sorts first)
    order = sorted(decade_counts, key=lambda d: (exact[d] - alloc[d], d or 0), reverse=True)
    for d in order[:leftover]:
        alloc[d] += 1
    return alloc


def similarity_graph(rows, max_similar):
    """rows of (xdid1, xdid2, matchpct) -> dict xdid -> set of similar xdids.

    gridcmp() reports a transposed match as a negative percentage, so the
    magnitude is what counts.
    """
    g = defaultdict(set)
    for a, b, pct in rows:
        try:
            pct = abs(int(pct))
        except (TypeError, ValueError):
            continue
        if a and b and a != b and pct >= max_similar:
            g[a].add(b)
            g[b].add(a)
    return g


def draw(candidates, seed, rate=1000, min_per_pub=1, similar=None, excluded=()):
    """Return (selected xdids in sorted order, per-stratum allocation report).

    candidates: iterable of Candidate (already filtered by window/redaction).
    similar: dict xdid -> set(xdid) from similarity_graph().
    excluded: xdids that must not be chosen and whose near-duplicates are
              also blocked (e.g. a previously released sample).
    """
    similar = similar or {}
    excluded = set(excluded)
    blocked = set(excluded)
    for x in excluded:
        blocked |= similar.get(x, set())

    strata = defaultdict(lambda: defaultdict(list))
    for c in candidates:
        if c.xdid in excluded:
            continue
        strata[c.pubid][decade_of(c.date)].append(c.xdid)

    selected = []
    report = []
    for pubid in sorted(strata):
        decades = strata[pubid]
        n = sum(len(v) for v in decades.values())
        k = quota(n, rate, min_per_pub)
        alloc = split_by_decade(k, {d: len(v) for d, v in decades.items()})
        for decade in sorted(decades, key=lambda d: d or 0):
            want = alloc[decade]
            pool = sorted(decades[decade])
            random.Random('%s:%s:%s' % (seed, pubid, decade)).shuffle(pool)
            got = 0
            for xdid in pool:
                if got >= want:
                    break
                if xdid in blocked:
                    continue
                selected.append(xdid)
                blocked.add(xdid)
                blocked |= similar.get(xdid, set())
                got += 1
            report.append((pubid, decade, len(pool), want, got))

    return sorted(selected), report
