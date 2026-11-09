#!/usr/bin/env python3
"""Draw the corpus growth chart for docs/HISTORY.md as a static SVG.

    history-chart.py <gxd-growth.csv> <out.svg>

gxd-growth.csv is written by corpus-stats.py (in the gxd-downloader repository) from a gxd
clone: one row per day of master's history with the running total of puzzles. The chart is
the running total over time with a few dated events marked. It is committed as an image so
the site stays static; regenerate it when the history page is reviewed.

Standard library only. Colors are mid-tones that read on light and dark backgrounds.
"""

import csv
import sys
from datetime import date

# The collection predates the repository: the gxd history starts in May 2016, and the puzzles
# committed over that summer were the collection Saul already had. The public record (the
# FiveThirtyEight coverage of March 2016) puts it at about 52,000 puzzles then; the dashed line
# draws that estimate from the start of the year to the first commit.
BEFORE_REPO = (date(2016, 1, 1), 52_000)

EVENTS = [
    # (date, label, dy) dy nudges the label up (negative) or down to avoid overlaps
    (date(2016, 3, 4), "FiveThirtyEight story", 30),
    (date(2016, 8, 26), "the collection is committed to git", -46),
    (date(2026, 9, 25), "The Cross Reference", -74),
    (date(2026, 10, 9), "Every Puzzle Project imports", -46),
    (date(2026, 11, 6), "centuryarcade.org", -18),
]

W, H = 900, 380
L, R, T, B = 70, 30, 40, 50
X0, X1 = date(2016, 1, 1), date(2027, 1, 1)
YMAX = 180_000
INK, MUTE, LINE = "#6b7a72", "#8e9a93", "#2f8f6b"


def xpos(d):
    return L + (d - X0).days / (X1 - X0).days * (W - L - R)


def ypos(v):
    return T + (1 - v / YMAX) * (H - T - B)


def main(src, out):
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    allpts = [(date.fromisoformat(r["day"]), int(r["total"])) for r in rows]
    first, last = allpts[0], allpts[-1]
    # thin the line: a day is kept when the total moved by 0.2% of the axis or two weeks have passed;
    # at this scale the thinned line is indistinguishable and the file is a tenth of the size
    pts, kept = [], None
    for d, t in allpts:
        if kept is None or abs(t - kept[1]) >= YMAX / 500 or (d - kept[0]).days >= 14:
            pts.append((d, t))
            kept = (d, t)
    if pts[-1] != last:
        pts.append(last)

    # step line: hold each total until the next day with a change
    path = [f"M{xpos(first[0]):.1f},{ypos(0):.1f}"]
    prev = 0
    for d, t in pts:
        path.append(f"L{xpos(d):.1f},{ypos(prev):.1f} L{xpos(d):.1f},{ypos(t):.1f}")
        prev = t
    path.append(f"L{xpos(last[0]):.1f},{ypos(prev):.1f}")
    d = " ".join(path)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" aria-label="Puzzles in the xd corpus, 2016 to {last[0].year}">',
         f'<title>Puzzles in the corpus, {first[0].isoformat()} to {last[0].isoformat()}</title>',
         f'<style>text{{font-family:system-ui,sans-serif;font-size:12px;fill:{INK}}}'
         f'.t{{font-size:11px;fill:{MUTE}}}.e{{font-size:11px;fill:{INK}}}</style>']

    for v in range(0, YMAX + 1, 30_000):
        y = ypos(v)
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{MUTE}" stroke-opacity="0.25"/>')
        o.append(f'<text class="t" x="{L-8}" y="{y+4:.1f}" text-anchor="end">{v//1000:,}k</text>')
    for yr in range(X0.year, X1.year + 1):
        x = xpos(date(yr, 1, 1))
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{H-B}" y2="{H-B+5}" stroke="{MUTE}"/>')
        if yr < X1.year:
            o.append(f'<text class="t" x="{xpos(date(yr, 7, 1)):.1f}" y="{H-B+18}" text-anchor="middle">{yr}</text>')

    o.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="2"/>')
    fill = d + f" L{xpos(last[0]):.1f},{ypos(0):.1f} Z"
    o.append(f'<path d="{fill}" fill="{LINE}" fill-opacity="0.08" stroke="none"/>')

    # the collection before the repository: a dashed estimate up to the first commit
    bx0, bx1, by = xpos(BEFORE_REPO[0]), xpos(first[0]), ypos(BEFORE_REPO[1])
    o.append(f'<line x1="{bx0:.1f}" x2="{bx1:.1f}" y1="{by:.1f}" y2="{by:.1f}" stroke="{LINE}" '
             f'stroke-width="2" stroke-dasharray="5 4" stroke-opacity="0.7"/>')
    o.append(f'<text class="e" x="{xpos(EVENTS[0][0]) + 8:.1f}" y="{by - 18:.1f}">about {BEFORE_REPO[1]:,} puzzles collected before the repository</text>')

    def total_at(day):
        if day < first[0]:
            return BEFORE_REPO[1]
        t = 0
        for dd, tt in pts:
            if dd > day:
                break
            t = tt
        return t

    for day, label, dy in EVENTS:
        if not label:
            continue
        x = xpos(day)
        y = ypos(total_at(day))
        anchor = "end" if x > W * 0.7 else "start"
        tx = x - 6 if anchor == "end" else x + 6
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{y + dy + 4:.1f}" y2="{y:.1f}" stroke="{INK}" stroke-opacity="0.6"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{INK}"/>')
        o.append(f'<text class="e" x="{tx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}">{label}</text>')

    o.append(f'<text class="t" x="{L}" y="{T-14}">Puzzles in the corpus, by day of the git repository\'s history, from {first[0]:%B %Y}. '
             f'Dashed: the collection before the repository, as counted in March 2016.</text>')
    o.append(f'<text class="t" x="{W-R}" y="{H-6}" text-anchor="end">{last[1]:,} puzzles on {last[0].day} {last[0]:%B %Y}</text>')
    o.append("</svg>")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(o) + "\n")
    print(f"{out}: {len(pts)} days, {first[0]} to {last[0]}, {last[1]:,} puzzles")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
