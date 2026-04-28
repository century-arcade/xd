#!/usr/bin/env python3
"""
xdlint.py - authoritative validator for the .xd crossword format.

Stdlib-only. The .xd format is specified in doc/xd-format.md; this script
enforces that spec and a curated set of style/quality rules derived from
real-world fixes in the gxd corpus.

Usage:
    xdlint.py path [path ...]              lint files / dirs (recursive)
    xdlint.py --base BASE [--head HEAD]    lint files changed in a git diff
    xdlint.py --list-rules                 print the rule catalog

Severity gate:
    --max-severity {error,warning,info}    default: error
    Exit 1 if any finding meets or exceeds the gate; else exit 0.

Rule selection:
    --disable XD###[,XD###...]
    --enable-only XD###[,XD###...]

Add a new rule:
    @rule("XD###", Severity.WARNING, "rule-name")
    def _(ctx):
        if condition:
            yield finding("XD###", Severity.WARNING, line, "message")
"""
from __future__ import annotations

import argparse
import enum
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 3, "warning": 2, "info": 1}[self.value]


@dataclass
class Finding:
    code: str
    severity: Severity
    line: int           # 1-indexed; 0 means file-level
    message: str


@dataclass
class Header:
    line: int
    key: str
    value: str


@dataclass
class GridRow:
    line: int
    cells: str          # the row with leading/trailing whitespace stripped


@dataclass
class Clue:
    line: int
    pos: str            # raw position string, e.g. "A1"
    direction: str      # "A", "D", or another single uppercase letter
    number: int         # parsed integer; -1 if non-numeric
    body: str           # clue text only
    answer: str
    raw: str
    metadata: dict = field(default_factory=dict)  # ^Key -> value (lowercased keys)


@dataclass
class ParsedXd:
    text: str
    lines: List[str]            # 0-indexed; line N is lines[N-1]
    section_mode: str           # 'implicit' | 'explicit'
    headers: List[Header]
    grid: List[GridRow]
    clues: List[Clue]
    notes_text: str
    parse_errors: List[Finding]


@dataclass
class Ctx:
    filename: str
    text: str
    parsed: ParsedXd


# ---------------------------------------------------------------------------
# Parser - strict, line-tracking, no silent normalization
# ---------------------------------------------------------------------------

EXPLICIT_HEADER_RE = re.compile(r"^\s*##\s+([A-Za-z][A-Za-z0-9_-]*)")
EXPLICIT_SECTIONS = {"metadata": "metadata", "grid": "grid", "clues": "clues", "notes": "notes"}
CLUE_META_RE = re.compile(r"^([A-Za-z][\w-]*)\s+\^([A-Za-z][\w-]*)\s*:\s*(.*)$")
CLUE_POS_RE = re.compile(r"^([A-Za-z])(\d+)$")


def parse(text: str) -> ParsedXd:
    lines = text.splitlines()
    parse_errors: List[Finding] = []

    # Pass 1: detect mode (explicit if any '## metadata|grid|clues|notes')
    section_mode = "implicit"
    for raw in lines:
        m = EXPLICIT_HEADER_RE.match(raw)
        if m and m.group(1).lower() in EXPLICIT_SECTIONS:
            section_mode = "explicit"
            break

    headers: List[Header] = []
    grid: List[GridRow] = []
    clues: List[Clue] = []
    notes_lines: List[str] = []

    section = "metadata"
    blank_run = 0
    started = False
    last_clue: Optional[Clue] = None
    implicit_order = ["metadata", "grid", "clues", "notes"]

    def advance_implicit():
        nonlocal section
        idx = implicit_order.index(section) if section in implicit_order else len(implicit_order) - 1
        if idx + 1 < len(implicit_order):
            section = implicit_order[idx + 1]

    for lineno0, raw in enumerate(lines):
        lineno = lineno0 + 1
        stripped = raw.strip()

        # Explicit '## Section' overrides everything
        if section_mode == "explicit":
            m = EXPLICIT_HEADER_RE.match(raw)
            if m:
                name = m.group(1).lower()
                if name in EXPLICIT_SECTIONS:
                    section = EXPLICIT_SECTIONS[name]
                    started = True
                    blank_run = 0
                    last_clue = None
                else:
                    # Per spec: unknown sections are ignored.
                    section = "_unknown"
                    blank_run = 0
                    last_clue = None
                continue

        if not stripped:
            blank_run += 1
            # Implicit-mode section advance: 2+ blank lines, but only after
            # we've seen real content (otherwise leading blanks would skip
            # past metadata).
            if section_mode == "implicit" and started and blank_run == 2:
                advance_implicit()
                last_clue = None
            continue

        started = True
        blank_run = 0

        if section == "metadata":
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                headers.append(Header(line=lineno, key=k.strip(), value=v.strip()))
            else:
                # Non key:value line in metadata: keep but flag
                parse_errors.append(Finding(
                    code="XD901", severity=Severity.WARNING, line=lineno,
                    message=f"non-header line in metadata section: {stripped!r}",
                ))

        elif section == "grid":
            grid.append(GridRow(line=lineno, cells=stripped))

        elif section == "clues":
            # Clue metadata: "A1 ^Key: value"
            mm = CLUE_META_RE.match(stripped)
            if mm and last_clue is not None and mm.group(1) == last_clue.pos:
                _, mkey, mval = mm.groups()
                last_clue.metadata[mkey.lower()] = mval.strip()
                continue
            # Normal clue: "A1. Body ~ ANSWER"
            ans_idx = stripped.rfind("~")
            if ans_idx > 0:
                head_part = stripped[:ans_idx].rstrip()
                answer = stripped[ans_idx + 1:].strip()
            else:
                head_part = stripped
                answer = ""
            dot = head_part.find(".")
            if dot <= 0:
                parse_errors.append(Finding(
                    code="XD901", severity=Severity.ERROR, line=lineno,
                    message=f"unrecognized line in clues section (no '.'): {stripped!r}",
                ))
                continue
            pos = head_part[:dot].strip()
            body = head_part[dot + 1:].strip()
            pm = CLUE_POS_RE.match(pos)
            if pm:
                direction = pm.group(1).upper()
                number = int(pm.group(2))
            else:
                direction = ""
                number = -1
            c = Clue(line=lineno, pos=pos, direction=direction, number=number,
                     body=body, answer=answer, raw=stripped)
            clues.append(c)
            last_clue = c

        else:  # notes or _unknown
            notes_lines.append(stripped)

    return ParsedXd(
        text=text, lines=lines, section_mode=section_mode,
        headers=headers, grid=grid, clues=clues,
        notes_text="\n".join(notes_lines), parse_errors=parse_errors,
    )


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

RuleFn = Callable[[Ctx], Iterator[Finding]]
RULES: List[tuple] = []  # (code, severity, name, fn)


def rule(code: str, severity: Severity, name: str):
    def deco(fn: RuleFn) -> RuleFn:
        RULES.append((code, severity, name, fn))
        return fn
    return deco


def finding(code: str, severity: Severity, line: int, message: str) -> Finding:
    return Finding(code=code, severity=severity, line=line, message=message)


# ---------------------------------------------------------------------------
# Helpers used by rules
# ---------------------------------------------------------------------------

# The spec calls out '#' as block, '_' as open/non-cell, '.' as wildcard.
# Asian variants U+25A0 / U+FF3F also appear in the existing parser.
BLOCK_CHARS = {"#", "_", "■", "＿"}
WILDCARD_CHAR = "."


def parse_rebus_header(value: str) -> dict:
    """Parse 'Rebus: 1=ONE 2=TWO' to {'1':'ONE', '2':'TWO'}.

    Tolerates the xd-crossword-tools 'A|B/AB' quantum syntax by taking
    everything before the first '/'. Tolerates whitespace around '='.
    """
    out = {}
    for part in value.split():
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if len(k) != 1:
            continue
        v = v.split("/")[0].strip()
        # Drop the '|' split character if present
        v = v.replace("|", "")
        out[k] = v.upper()
    return out


def get_header(parsed: ParsedXd, key: str) -> Optional[str]:
    for h in parsed.headers:
        if h.key.lower() == key.lower():
            return h.value
    return None


def grid_get(grid: List[GridRow], r: int, c: int) -> str:
    if r < 0 or r >= len(grid):
        return "#"
    row = grid[r].cells
    if c < 0 or c >= len(row):
        return "#"
    return row[c]


def is_boundary(grid: List[GridRow], r: int, c: int) -> bool:
    return grid_get(grid, r, c) in BLOCK_CHARS


def enumerate_slots(grid: List[GridRow], rebus_map: dict):
    """Yield slots from the grid in canonical xd numbering order.

    Returns list of (direction, num, r, c, cells, grid_answer).
        direction: 'A' or 'D'
        cells: list of (r, c) covering the slot
        grid_answer: rebus-expanded uppercased answer, with wildcard '.'
                     preserved as '.'
    """
    slots = []
    if not grid:
        return slots
    num = 1
    for r in range(len(grid)):
        row_len = len(grid[r].cells)
        for c in range(row_len):
            if is_boundary(grid, r, c):
                continue
            new_clue = False
            # Across slot start
            if is_boundary(grid, r, c - 1):
                cc = c
                cells = []
                while not is_boundary(grid, r, cc):
                    cells.append((r, cc))
                    cc += 1
                if len(cells) > 1:
                    new_clue = True
                    slots.append(("A", num, r, c, cells,
                                  _build_answer(cells, grid, rebus_map)))
            # Down slot start
            if is_boundary(grid, r - 1, c):
                rr = r
                cells = []
                while not is_boundary(grid, rr, c):
                    cells.append((rr, c))
                    rr += 1
                if len(cells) > 1:
                    new_clue = True
                    slots.append(("D", num, r, c, cells,
                                  _build_answer(cells, grid, rebus_map)))
            if new_clue:
                num += 1
    return slots


def _build_answer(cells, grid, rebus_map) -> str:
    out = []
    for (r, c) in cells:
        ch = grid_get(grid, r, c)
        if ch in rebus_map:
            out.append(rebus_map[ch])
        elif ch == WILDCARD_CHAR:
            out.append(".")
        else:
            out.append(ch.upper())
    return "".join(out)


# Memoize slot enumeration on the ctx so multiple structural rules don't
# repeat the work. Keyed by id(ctx) since Ctx isn't hashable.
_SLOT_CACHE: dict = {}


def slots_for(ctx: Ctx):
    key = id(ctx)
    if key in _SLOT_CACHE:
        return _SLOT_CACHE[key]
    rebus = parse_rebus_header(get_header(ctx.parsed, "Rebus") or "")
    slots = enumerate_slots(ctx.parsed.grid, rebus)
    _SLOT_CACHE[key] = slots
    return slots


def grid_is_rectangular(parsed: ParsedXd) -> bool:
    if not parsed.grid:
        return True
    widths = {len(g.cells) for g in parsed.grid}
    return len(widths) == 1


# ---------------------------------------------------------------------------
# Rules - errors
# ---------------------------------------------------------------------------

@rule("XD001", Severity.ERROR, "rectangular-grid")
def _(ctx):
    if not ctx.parsed.grid:
        return
    first_w = len(ctx.parsed.grid[0].cells)
    for g in ctx.parsed.grid:
        if len(g.cells) != first_w:
            yield finding("XD001", Severity.ERROR, g.line,
                          f"row width {len(g.cells)} != first row width {first_w}")


def _has_quantum_rebus(parsed: ParsedXd) -> bool:
    return "/" in (get_header(parsed, "Rebus") or "")


@rule("XD007", Severity.ERROR, "answer-grid-coherence")
def _(ctx):
    """Combined: missing slot for clue (XD004), length mismatch (XD006),
    letter mismatch (XD007). All three are emitted under XD007 in the
    first pass; we'll split into separate rule codes once we have a
    granular --disable mechanism that justifies the boilerplate.

    Skip path is announced by XD108 when a quantum-rebus puzzle is
    detected, so silent passes are visible to the user."""
    if not ctx.parsed.grid or not ctx.parsed.clues:
        return
    if not grid_is_rectangular(ctx.parsed):
        return  # XD001 fires; slot enumeration unreliable
    if _has_quantum_rebus(ctx.parsed):
        return  # XD108 announces the skip

    slots = slots_for(ctx)
    by_pos = {f"{d}{n}": (cells, ans) for (d, n, _r, _c, cells, ans) in slots}

    for clue in ctx.parsed.clues:
        if not clue.answer:
            continue
        if clue.direction not in ("A", "D"):
            continue  # uniclue / non-AD: skip in first pass
        if clue.pos not in by_pos:
            yield finding("XD007", Severity.ERROR, clue.line,
                          f"clue {clue.pos} has no corresponding slot in grid")
            continue
        cells, grid_ans = by_pos[clue.pos]
        # Strip the xd-tools split character; uppercase
        declared = clue.answer.replace("|", "").upper()
        if len(declared) != len(grid_ans):
            yield finding("XD007", Severity.ERROR, clue.line,
                          f"clue {clue.pos} answer length {len(declared)} "
                          f"!= grid run length {len(grid_ans)} "
                          f"(declared={declared!r}, grid={grid_ans!r})")
            continue
        for a, b in zip(declared, grid_ans):
            if a == "." or b == ".":
                continue  # wildcard
            if a != b:
                yield finding("XD007", Severity.ERROR, clue.line,
                              f"clue {clue.pos} answer doesn't match grid: "
                              f"declared={declared!r}, grid={grid_ans!r}")
                break


_C1_RE = re.compile(r"[\x80-\x9f]")


@rule("XD010", Severity.ERROR, "bad-codepoint")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        m = _C1_RE.search(line)
        if m:
            cp = ord(m.group(0))
            yield finding("XD010", Severity.ERROR, i,
                          f"C1 control U+{cp:04X} at col {m.start() + 1} "
                          f"(likely Windows-1252 mojibake)")


_HTML_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]{1,8}|#\d+|#x[0-9a-fA-F]+);")


@rule("XD011", Severity.ERROR, "html-entity")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        m = _HTML_ENTITY_RE.search(line)
        if m:
            yield finding("XD011", Severity.ERROR, i,
                          f"HTML-entity-shaped token {m.group(0)!r} at col {m.start() + 1}")


@rule("XD020", Severity.ERROR, "missing-required-section")
def _(ctx):
    """Per spec, the file has metadata, grid, and clues sections.
    Notes is optional."""
    if not ctx.parsed.headers:
        yield finding("XD020", Severity.ERROR, 0, "no metadata section found")
    if not ctx.parsed.grid:
        yield finding("XD020", Severity.ERROR, 0, "no grid section found")
    if not ctx.parsed.clues:
        yield finding("XD020", Severity.ERROR, 0, "no clues section found")


@rule("XD016", Severity.ERROR, "no-letters-in-grid")
def _(ctx):
    if not ctx.parsed.grid:
        return  # XD020 covers this
    has_cell = any(
        ch.isalpha() or ch.isdigit()
        for row in ctx.parsed.grid
        for ch in row.cells
        if ch not in BLOCK_CHARS and ch != WILDCARD_CHAR
    )
    if not has_cell:
        yield finding("XD016", Severity.ERROR, ctx.parsed.grid[0].line,
                      "grid contains no answer cells")


# ---------------------------------------------------------------------------
# Rules - warnings
# ---------------------------------------------------------------------------

# A clue body that mentions another clue position. The space variant
# requires a hyphen-or-space between the number and "Across"/"Down" to
# avoid matching everyday phrases like "stayed across".
_CROSSREF_RE = re.compile(r"\b(\d+)[-\s](?:[Aa]cross|[Dd]own)\b")


@rule("XD108", Severity.WARNING, "answer-check-skipped")
def _(ctx):
    """Announce when XD007 was skipped due to a feature we don't yet
    model. Currently fires only for quantum-letter rebus syntax
    ('A/B' in a Rebus value)."""
    if not ctx.parsed.grid or not ctx.parsed.clues:
        return
    if not _has_quantum_rebus(ctx.parsed):
        return
    line = 0
    for h in ctx.parsed.headers:
        if h.key.lower() == "rebus":
            line = h.line
            break
    yield finding("XD108", Severity.WARNING, line,
                  "answer/grid check (XD007) skipped: quantum-letter rebus "
                  "syntax 'A/B' not yet supported by the linter")


@rule("XD013", Severity.INFO, "missing-refs-metadata")
def _(ctx):
    for clue in ctx.parsed.clues:
        if _CROSSREF_RE.search(clue.body):
            if "refs" not in clue.metadata:
                yield finding("XD013", Severity.INFO, clue.line,
                              f"clue {clue.pos} references another clue "
                              f"but has no '^Refs:' metadata")


# ---------------------------------------------------------------------------
# Driver: source of (path, ctx) pairs
# ---------------------------------------------------------------------------

def iter_xd_paths(roots):
    """Yield .xd file paths under each root (file or directory)."""
    for root in roots:
        if os.path.isfile(root):
            if root.endswith(".xd"):
                yield root
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".xd"):
                    yield os.path.join(dirpath, fn)


def contexts_from_paths(paths):
    for path in iter_xd_paths(paths):
        try:
            with open(path, "rb") as f:
                data = f.read()
            text = data.decode("utf-8", errors="replace")
        except OSError as e:
            print(f"{path}\tIO\terror reading: {e}", file=sys.stderr)
            continue
        yield path, Ctx(filename=path, text=text, parsed=parse(text))


def _git(*args):
    return subprocess.check_output(["git", *args], text=True, errors="replace")


def _batch_show(ref, paths):
    """Fetch many blobs in one cat-file --batch invocation. Each lookup is
    a network round-trip on a partial clone, so batching matters in CI."""
    if not paths:
        return {}
    stdin = b"".join((f"{ref}:{p}\n").encode() for p in paths)
    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=stdin, capture_output=True, check=True,
    )
    data = proc.stdout
    result = {}
    pos = 0
    for path in paths:
        nl = data.index(b"\n", pos)
        header = data[pos:nl]
        pos = nl + 1
        parts = header.split(b" ")
        if len(parts) >= 2 and parts[-1] == b"missing":
            result[path] = None
            continue
        if len(parts) < 3:
            result[path] = None
            continue
        size = int(parts[2])
        result[path] = data[pos:pos + size]
        pos += size + 1
    return result


def contexts_from_git(base, head):
    """Lint files added or modified between two refs."""
    out = _git("diff", "--name-only", "--diff-filter=AM", f"{base}..{head}")
    paths = [p for p in out.splitlines() if p.endswith(".xd")]
    blobs = _batch_show(head, paths)
    for path in paths:
        content = blobs.get(path)
        if content is None:
            continue
        text = content.decode("utf-8", errors="replace")
        yield path, Ctx(filename=path, text=text, parsed=parse(text))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_checks(ctx: Ctx, active_codes):
    """Yield findings from the parser plus all active rules."""
    for f in ctx.parsed.parse_errors:
        if active_codes is None or f.code in active_codes:
            yield f
    for code, severity, _name, fn in RULES:
        if active_codes is not None and code not in active_codes:
            continue
        try:
            yield from fn(ctx)
        except Exception as e:
            yield finding(code, severity, 0,
                          f"rule raised {type(e).__name__}: {e}")


def format_finding(path, f: Finding) -> str:
    loc = f"{path}:{f.line}" if f.line else path
    return f"{loc}\t{f.severity.value}\t{f.code}\t{f.message}"


def main():
    # Findings can contain any Unicode (clue text, mojibake bytes, etc).
    # On Windows the default console encoding is cp1252 and will crash on
    # non-Latin output. Force UTF-8 on both streams.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("paths", nargs="*", help=".xd files or directories")
    ap.add_argument("--base", help="git diff base sha/ref (enables diff mode)")
    ap.add_argument("--head", default="HEAD", help="git diff head (default: HEAD)")
    ap.add_argument("--max-severity",
                    choices=["error", "warning", "info"], default="error",
                    help="exit nonzero if a finding meets this level (default: error)")
    ap.add_argument("--disable", default="",
                    help="comma-separated rule codes to skip (e.g. XD013,XD016)")
    ap.add_argument("--enable-only", default="",
                    help="comma-separated rule codes to run (overrides --disable)")
    ap.add_argument("--list-rules", action="store_true",
                    help="print the rule catalog and exit")
    args = ap.parse_args()

    if args.list_rules:
        print(f"{'CODE':<8} {'SEVERITY':<8} NAME")
        for code, sev, name, _ in sorted(RULES):
            print(f"{code:<8} {sev.value:<8} {name}")
        return 0

    if args.enable_only:
        active = {c.strip() for c in args.enable_only.split(",") if c.strip()}
    elif args.disable:
        disabled = {c.strip() for c in args.disable.split(",") if c.strip()}
        active = {code for (code, _s, _n, _f) in RULES} - disabled
        # parse_errors codes (XD9xx) stay enabled unless explicitly disabled
        active |= {"XD901"} - disabled
    else:
        active = None

    if args.base:
        source = contexts_from_git(args.base, args.head)
    elif args.paths:
        source = contexts_from_paths(args.paths)
    else:
        ap.error("give --base for git-diff mode, or explicit .xd paths")

    gate_rank = Severity(args.max_severity).rank
    checked = 0
    findings_total = 0
    gate_hit = 0

    for path, ctx in source:
        checked += 1
        for f in run_checks(ctx, active):
            print(format_finding(path, f))
            findings_total += 1
            if f.severity.rank >= gate_rank:
                gate_hit += 1
        # Drop the slot cache for this ctx; otherwise large corpus runs
        # accumulate one entry per file forever.
        _SLOT_CACHE.pop(id(ctx), None)

    print(f"\nchecked {checked} file(s), {findings_total} finding(s), "
          f"{gate_hit} at or above '{args.max_severity}'", file=sys.stderr)
    return 1 if gate_hit > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
