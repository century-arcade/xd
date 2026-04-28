#!/usr/bin/env python3
"""
xdlint.py - authoritative validator for the .xd crossword format.

Stdlib-only. The .xd format is specified in doc/xd-format.md; this script
enforces that spec and a curated set of style/quality rules derived from
patterns that have repeatedly required hand-fixing in our own xd file corpus.

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
from typing import Callable, Dict, Iterator, List, Optional, Tuple


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
                # Non key:value line in metadata: typically caused by a
                # missing section separator (need 2+ blank lines between
                # metadata and grid, only 1 was found).
                parse_errors.append(Finding(
                    code="XD019", severity=Severity.WARNING, line=lineno,
                    message=f"non-header line in metadata section "
                            f"(likely missing 2+ blank lines before grid): "
                            f"{stripped!r}",
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
                    code="XD012", severity=Severity.ERROR, line=lineno,
                    message=f"unrecognized line in clues section "
                            f"(no '.', likely an embedded newline): {stripped!r}",
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
RULES: List[tuple] = []  # (code, severity, name, experimental, fn)


def rule(code: str, severity: Severity, name: str, experimental: bool = False):
    """Register a check.

    experimental=True marks rules whose validation depends on conventions
    not formalized in the spec (currently: rules that interpret quantum
    or Schrödinger rebus syntax). Disabled by --no-experimental.
    """
    def deco(fn: RuleFn) -> RuleFn:
        RULES.append((code, severity, name, experimental, fn))
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


@dataclass
class RebusExpansion:
    """Per-direction list of valid expansions for a rebus key.

    Conventions (extension to xd-format spec, not yet formalized):
        '/' separates across vs down readings:  1=IE/EI
        '|' separates Schrödinger alternates:   1=A|B  (any letter, any direction)
        Both compose, '|' precedence within '/' halves: 1=SE/S|E
        Empty halves of '/' mean literal slash: 1=/   (cell is the '/' character)

    For non-quantum rebus, across == down == [single value].
    """
    across: List[str]   # acceptable expansions when slot is read across
    down: List[str]     # acceptable expansions when slot is read down

    @property
    def is_directional(self) -> bool:
        return self.across != self.down

    def is_schrodinger(self, direction_idx: int) -> bool:
        return len((self.across, self.down)[direction_idx]) > 1


def _split_alternatives(s: str) -> List[str]:
    """Split on '|' if it acts as an operator (2+ non-empty parts).
    Otherwise treat the whole string as a single literal value."""
    if "|" in s:
        parts = s.split("|")
        if len(parts) >= 2 and all(parts):
            return [p.upper() for p in parts]
    return [s.upper()]


def parse_rebus_value(value: str) -> RebusExpansion:
    """Parse one rebus value (the part after '=' in 'key=value').

    See RebusExpansion docstring for the convention this implements.
    """
    if "/" in value:
        slash_idx = value.index("/")
        before = value[:slash_idx]
        after = value[slash_idx + 1:]
        if before and after:
            # Directional split.
            return RebusExpansion(
                across=_split_alternatives(before),
                down=_split_alternatives(after),
            )
        # Empty half(s): '/' is the literal cell content, not an operator.
    alts = _split_alternatives(value)
    return RebusExpansion(across=alts, down=alts)


def parse_rebus_header(value: str) -> Dict[str, RebusExpansion]:
    """Parse 'Rebus: 1=ONE 2=TWO 3=A/B' into {key: RebusExpansion}."""
    out: Dict[str, RebusExpansion] = {}
    for part in value.split():
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if len(k) != 1:
            continue
        out[k] = parse_rebus_value(v)
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


def enumerate_slots(grid: List[GridRow]):
    """Yield slots from the grid in canonical xd numbering order.

    Returns list of (direction, num, r, c, cells).
        direction: 'A' or 'D'
        cells: list of (r, c) covering the slot

    Answer expansion is intentionally NOT baked in: under the quantum
    rebus convention each cell may have multiple direction-dependent
    expansions, so the validator computes them per-clue.
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
                    slots.append(("A", num, r, c, cells))
            # Down slot start
            if is_boundary(grid, r - 1, c):
                rr = r
                cells = []
                while not is_boundary(grid, rr, c):
                    cells.append((rr, c))
                    rr += 1
                if len(cells) > 1:
                    new_clue = True
                    slots.append(("D", num, r, c, cells))
            if new_clue:
                num += 1
    return slots


# Memoize slot enumeration on the ctx so multiple structural rules don't
# repeat the work. Keyed by id(ctx) since Ctx isn't hashable.
_SLOT_CACHE: dict = {}


def slots_for(ctx: Ctx):
    key = id(ctx)
    if key in _SLOT_CACHE:
        return _SLOT_CACHE[key]
    slots = enumerate_slots(ctx.parsed.grid)
    _SLOT_CACHE[key] = slots
    return slots


def _validate_answer_against_slot(
    declared: str,
    cells: List[Tuple[int, int]],
    grid: List[GridRow],
    rebus_map: Dict[str, RebusExpansion],
    direction_idx: int,
) -> Optional[Tuple[str, str]]:
    """Walk the declared answer and slot cells in lockstep.

    Returns None on success. Returns (code, message) on failure where
    code is 'XD006' for length problems and 'XD007' for letter problems.

    Handles three answer styles per cell:
      - Plain (single-letter or rebus, no quantum syntax)
      - Schrödinger '|' alternates: try each
      - Inline '<across>/<down>' form: when a rebus has exactly one
        across-alt and one down-alt and they differ, the declared
        answer may embed both inline (e.g. STOOLEI/IE for 1=EI/IE).

    The xd-crossword-tools '|' word-split convention is stripped from
    the declared answer first (harmless for plain rebus; for Schrödinger
    answers we don't expect '|' to appear since each clue picks one
    alternative).
    """
    declared = declared.replace("|", "")
    di = 0
    for (r, c) in cells:
        ch = grid_get(grid, r, c)
        if ch in rebus_map:
            rebus = rebus_map[ch]
            chosen = rebus.across if direction_idx == 0 else rebus.down
            # Try inline '<across>/<down>' first when both directions
            # have a single distinct expansion.
            if (len(rebus.across) == 1 and len(rebus.down) == 1
                    and rebus.across[0] != rebus.down[0]):
                full = rebus.across[0] + "/" + rebus.down[0]
                if declared[di:di + len(full)].upper() == full:
                    di += len(full)
                    continue
            # Otherwise match one of the chosen direction's alts.
            matched = False
            for alt in chosen:
                if declared[di:di + len(alt)].upper() == alt:
                    di += len(alt)
                    matched = True
                    break
            if not matched:
                if di >= len(declared):
                    return ("XD006", "answer too short for slot")
                expected = " or ".join(repr(a) for a in chosen)
                fragment = declared[di:di + max((len(a) for a in chosen), default=1)]
                return ("XD007", f"at position {di + 1}: expected {expected}, "
                                 f"found {fragment!r}")
        elif ch == WILDCARD_CHAR:
            if di >= len(declared):
                return ("XD006", "answer too short for slot")
            di += 1  # wildcard accepts anything
        else:
            if di >= len(declared):
                return ("XD006", "answer too short for slot")
            if declared[di].upper() != ch.upper():
                return ("XD007", f"at position {di + 1}: expected "
                                 f"{ch.upper()!r}, found {declared[di]!r}")
            di += 1
    if di < len(declared):
        return ("XD006", f"answer has {len(declared) - di} extra char(s) "
                         f"after position {di}")
    return None


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


@rule("XD002", Severity.ERROR, "unrecognized-grid-char")
def _(ctx):
    """Grid cell that isn't a letter, block, wildcard, or declared rebus key."""
    rebus = parse_rebus_header(get_header(ctx.parsed, "Rebus") or "")
    seen_pairs = set()  # de-dup to one finding per (line, char)
    for row in ctx.parsed.grid:
        for col, ch in enumerate(row.cells, 1):
            if ch in BLOCK_CHARS or ch == WILDCARD_CHAR or ch.isalpha():
                continue
            if ch in rebus:
                continue
            key = (row.line, ch)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            yield finding("XD002", Severity.ERROR, row.line,
                          f"unrecognized grid character {ch!r} at col {col}")


@rule("XD003", Severity.ERROR, "rebus-key-not-in-grid")
def _(ctx):
    rebus_header = next((h for h in ctx.parsed.headers
                         if h.key.lower() == "rebus"), None)
    if rebus_header is None:
        return
    rebus = parse_rebus_header(rebus_header.value)
    if not rebus:
        return
    used = set()
    for row in ctx.parsed.grid:
        used.update(row.cells)
    for k in rebus:
        if k not in used:
            yield finding("XD003", Severity.ERROR, rebus_header.line,
                          f"rebus key {k!r} declared but never used in grid")


def _slot_index_or_none(ctx):
    """Build {pos: (direction, cells)} for the rectangular case.
    Returns None when the answer-grid family of rules can't run.

    Quantum/Schrödinger rebuses are *not* a skip path — the validator
    handles them.
    """
    if not ctx.parsed.grid or not ctx.parsed.clues:
        return None
    if not grid_is_rectangular(ctx.parsed):
        return None  # XD001 covers it; slot enumeration is unreliable
    slots = slots_for(ctx)
    return {f"{d}{n}": (d, cells) for (d, n, _r, _c, cells) in slots}


def _rebus_for(ctx) -> Dict[str, RebusExpansion]:
    """Memoized rebus map per ctx."""
    cache = getattr(ctx, "_rebus_cache", None)
    if cache is not None:
        return cache
    cache = parse_rebus_header(get_header(ctx.parsed, "Rebus") or "")
    ctx._rebus_cache = cache
    return cache


@rule("XD004", Severity.ERROR, "missing-slot-for-clue")
def _(ctx):
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    for clue in ctx.parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            yield finding("XD004", Severity.ERROR, clue.line,
                          f"clue {clue.pos} has no corresponding slot in grid")


@rule("XD005", Severity.ERROR, "clue-count-mismatch")
def _(ctx):
    """Compares distinct clue *positions* (not total clues) to slot count.
    Schrödinger puzzles legitimately have multiple clues at the same
    position, so counting positions rather than clues handles that."""
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    if any(c.direction not in ("A", "D") for c in ctx.parsed.clues):
        return
    n_slots = len(idx)
    n_positions = len({c.pos for c in ctx.parsed.clues if c.pos})
    if n_slots != n_positions:
        line = ctx.parsed.clues[0].line if ctx.parsed.clues else 0
        yield finding("XD005", Severity.ERROR, line,
                      f"distinct clue positions {n_positions} "
                      f"!= grid slot count {n_slots}")


@rule("XD006", Severity.ERROR, "answer-length-mismatch", experimental=True)
def _(ctx):
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    rebus_map = _rebus_for(ctx)
    for clue in ctx.parsed.clues:
        if not clue.answer or clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            continue  # XD004 fires
        direction, cells = idx[clue.pos]
        direction_idx = 0 if direction == "A" else 1
        result = _validate_answer_against_slot(
            clue.answer, cells, ctx.parsed.grid, rebus_map, direction_idx,
        )
        if result is not None and result[0] == "XD006":
            yield finding("XD006", Severity.ERROR, clue.line,
                          f"clue {clue.pos}: {result[1]} "
                          f"(declared={clue.answer!r})")


@rule("XD007", Severity.ERROR, "answer-grid-letter-mismatch", experimental=True)
def _(ctx):
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    rebus_map = _rebus_for(ctx)
    for clue in ctx.parsed.clues:
        if not clue.answer or clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            continue
        direction, cells = idx[clue.pos]
        direction_idx = 0 if direction == "A" else 1
        result = _validate_answer_against_slot(
            clue.answer, cells, ctx.parsed.grid, rebus_map, direction_idx,
        )
        if result is not None and result[0] == "XD007":
            yield finding("XD007", Severity.ERROR, clue.line,
                          f"clue {clue.pos}: {result[1]} "
                          f"(declared={clue.answer!r})")


@rule("XD008", Severity.ERROR, "duplicate-clue-position", experimental=True)
def _(ctx):
    """Two clues at the same position are legal only when the slot
    contains a Schrödinger cell in that direction (the puzzle author
    is providing a separate clue for each valid letter-choice reading)."""
    idx = _slot_index_or_none(ctx)
    rebus_map = _rebus_for(ctx)
    seen = {}
    for clue in ctx.parsed.clues:
        if not clue.pos:
            continue
        if clue.pos not in seen:
            seen[clue.pos] = clue.line
            continue
        # Duplicate. Allow if the slot has any Schrödinger cell for
        # this direction.
        allowed = False
        if idx and clue.pos in idx and clue.direction in ("A", "D"):
            direction, cells = idx[clue.pos]
            direction_idx = 0 if direction == "A" else 1
            for (r, c) in cells:
                ch = grid_get(ctx.parsed.grid, r, c)
                if ch in rebus_map and rebus_map[ch].is_schrodinger(direction_idx):
                    allowed = True
                    break
        if not allowed:
            yield finding("XD008", Severity.ERROR, clue.line,
                          f"clue position {clue.pos} duplicated "
                          f"(first seen at line {seen[clue.pos]})")


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


_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@rule("XD009", Severity.ERROR, "filename-date-mismatch")
def _(ctx):
    """Catches files saved under a date the puzzle wasn't published on
    (e.g. a 2021 file containing a 2018 puzzle). Skips files whose name
    has no date."""
    fn = os.path.basename(ctx.filename)
    fn_match = _ISO_DATE_RE.search(fn)
    if not fn_match:
        return
    hdr_date = get_header(ctx.parsed, "Date") or ""
    hdr_match = _ISO_DATE_RE.search(hdr_date)
    if not hdr_match:
        return  # XD105 covers malformed Date headers
    if fn_match.group(1) != hdr_match.group(1):
        line = next((h.line for h in ctx.parsed.headers
                     if h.key.lower() == "date"), 0)
        yield finding("XD009", Severity.ERROR, line,
                      f"filename date {fn_match.group(1)} doesn't match "
                      f"Date header {hdr_match.group(1)}")


@rule("XD014", Severity.ERROR, "broken-ref")
def _(ctx):
    """Clue's ^Refs metadata names a position that doesn't exist."""
    positions = {c.pos for c in ctx.parsed.clues if c.pos}
    for clue in ctx.parsed.clues:
        refs = clue.metadata.get("refs")
        if not refs:
            continue
        for token in refs.split():
            if token not in positions:
                yield finding("XD014", Severity.ERROR, clue.line,
                              f"clue {clue.pos} ^Refs points to "
                              f"non-existent clue {token}")


@rule("XD015", Severity.WARNING, "answer-word-in-clue")
def _(ctx):
    """xd-crossword-tools' anti-cheat lint: a word of the answer (after
    '|' splits) appears verbatim in the clue body. Only runs when the
    answer has explicit '|' word splits, since otherwise we can't tell
    where the word boundaries are."""
    for clue in ctx.parsed.clues:
        if not clue.answer or "|" not in clue.answer:
            continue
        body_words = set(re.findall(r"[a-z]{3,}", clue.body.lower()))
        for word in clue.answer.lower().split("|"):
            if len(word) < 3 or not word.isalpha():
                continue
            if word in body_words:
                yield finding("XD015", Severity.WARNING, clue.line,
                              f"clue {clue.pos} answer word {word!r} "
                              f"appears verbatim in clue body")
                break  # one finding per clue


_VALID_CLUE_POS_RE = re.compile(r"^[A-Za-z]?\d+$")


@rule("XD017", Severity.WARNING, "malformed-clue-position")
def _(ctx):
    """Clue position before '.' should be 'A1'/'D27' (normal A/D),
    a single cluegroup letter + digits (e.g. 'X1.'), or just digits
    (uniclue). Anything else (stray space, trailing junk, OCR-style
    typo) lands here. Also surfaces clues that XD004/XD006/XD007
    silently skip because their position couldn't be parsed."""
    for clue in ctx.parsed.clues:
        if not _VALID_CLUE_POS_RE.match(clue.pos):
            yield finding("XD017", Severity.WARNING, clue.line,
                          f"clue position {clue.pos!r} doesn't match "
                          f"expected form (e.g. 'A1', 'D27', or '5' for uniclue)")


@rule("XD018", Severity.INFO, "multiple-tilde-separators")
def _(ctx):
    """A clue line with more than one ' ~ ' (tilde with spaces both
    sides — the spec separator). Parsers may disagree on which is the
    answer divider. A single tilde without surrounding spaces inside
    clue text is legal and not flagged."""
    for clue in ctx.parsed.clues:
        if clue.raw.count(" ~ ") > 1:
            yield finding("XD018", Severity.INFO, clue.line,
                          "clue line has multiple ' ~ ' separators "
                          "(parsers may pick different splits)")


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

@rule("XD101", Severity.WARNING, "backslash-in-clue")
def _(ctx):
    """Backslashes in clue bodies are almost always import bugs:
    '\\--', 'Moore\\Peters', '<\\I>', '¯\\_(tsu)_/¯' are all real
    historical fixes. The spec sanctions a single trailing '\\' as
    a multi-line clue continuation, but it's effectively unused in
    the corpus and the project direction is to drop the special
    meaning entirely; flagging all backslashes."""
    for clue in ctx.parsed.clues:
        if "\\" in clue.body:
            col = clue.raw.find("\\") + 1
            yield finding("XD101", Severity.WARNING, clue.line,
                          f"backslash at col {col} (likely an import artifact)")


@rule("XD102", Severity.WARNING, "extra-blank-lines-in-clues")
def _(ctx):
    """In the clues section, 2+ consecutive blank lines splits it into
    separate sections in spec-compliant parsers. The Across/Down boundary
    is supposed to be a single blank line."""
    if not ctx.parsed.clues:
        return
    first = ctx.parsed.clues[0].line
    last = ctx.parsed.clues[-1].line
    blank_run = 0
    run_start = 0
    for i in range(first, last + 1):
        line = ctx.parsed.lines[i - 1] if i - 1 < len(ctx.parsed.lines) else ""
        if not line.strip():
            if blank_run == 0:
                run_start = i
            blank_run += 1
        else:
            if blank_run >= 2:
                yield finding("XD102", Severity.WARNING, run_start,
                              f"{blank_run} consecutive blank lines in clues "
                              f"section (2+ splits the section)")
            blank_run = 0


_AUTHOR_EDITOR_RE = re.compile(r"/\s*Ed(?:itor|\.)?\b|edited by", re.IGNORECASE)


@rule("XD103", Severity.WARNING, "editor-folded-into-author")
def _(ctx):
    """Catches 'Author: X / Ed. Y' style; split into separate Author and
    Editor headers."""
    for h in ctx.parsed.headers:
        if h.key.lower() != "author":
            continue
        if _AUTHOR_EDITOR_RE.search(h.value):
            yield finding("XD103", Severity.WARNING, h.line,
                          "Author value looks like it includes the editor; "
                          "split into separate Author and Editor headers")


# Canonical metadata header keys, in conventional ordering. Source of
# truth: xdfile.HEADER_ORDER.
HEADER_ORDER = [
    "title", "author", "editor", "copyright", "number", "date",
    "relation", "special", "rebus", "cluegroup", "description", "notes",
]
CANONICAL_HEADERS = set(HEADER_ORDER)


@rule("XD104", Severity.WARNING, "non-standard-special-value")
def _(ctx):
    valid = {"shaded", "circle"}
    for h in ctx.parsed.headers:
        if h.key.lower() != "special":
            continue
        if h.value.lower() not in valid:
            yield finding("XD104", Severity.WARNING, h.line,
                          f"Special value {h.value!r} not in {{shaded, circle}}")


_FULL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@rule("XD105", Severity.WARNING, "non-iso-date-header")
def _(ctx):
    for h in ctx.parsed.headers:
        if h.key.lower() != "date":
            continue
        if not _FULL_DATE_RE.match(h.value):
            yield finding("XD105", Severity.WARNING, h.line,
                          f"Date header {h.value!r} not in YYYY-MM-DD form")


@rule("XD106", Severity.WARNING, "missing-recommended-header")
def _(ctx):
    """Title and Date are practically required. Author is recommended
    but not flagged here, since author can be present but messy
    ('Author: X / Ed. Y' style — XD103 catches that)."""
    keys = {h.key.lower() for h in ctx.parsed.headers}
    for required in ("title", "date"):
        if required not in keys:
            yield finding("XD106", Severity.WARNING, 0,
                          f"missing recommended header {required.title()!r}")


@rule("XD107", Severity.WARNING, "duplicate-header-key")
def _(ctx):
    seen = {}
    for h in ctx.parsed.headers:
        k = h.key.lower()
        if k in seen:
            yield finding("XD107", Severity.WARNING, h.line,
                          f"duplicate header key {h.key!r} "
                          f"(first at line {seen[k]})")
        else:
            seen[k] = h.line


_INDENTED_HEADER_RE = re.compile(r"^[ \t]+##\s+")


@rule("XD110", Severity.WARNING, "indented-section-header")
def _(ctx):
    """A '## Section' line with leading whitespace; per xd-crossword-tools'
    strict mode, this is likely an accidental indentation."""
    for i, line in enumerate(ctx.parsed.lines, 1):
        if _INDENTED_HEADER_RE.match(line):
            yield finding("XD110", Severity.WARNING, i,
                          "'## Section' header has leading whitespace")


@rule("XD111", Severity.WARNING, "non-canonical-header-key")
def _(ctx):
    """Header key isn't one of the spec-canonical ones. Catches typos
    ('Note' instead of 'Notes') and tool-specific extensions. Spec says
    additional headers are 'allowed but ignored', so this stays at
    warning level."""
    for h in ctx.parsed.headers:
        if h.key.lower() not in CANONICAL_HEADERS:
            yield finding("XD111", Severity.WARNING, h.line,
                          f"non-canonical header key {h.key!r} "
                          f"(canonical set: {sorted(CANONICAL_HEADERS)})")


# A clue body that mentions another clue position. The space variant
# requires a hyphen-or-space between the number and "Across"/"Down" to
# avoid matching everyday phrases like "stayed across".
_CROSSREF_RE = re.compile(r"\b(\d+)[-\s](?:[Aa]cross|[Dd]own)\b")


@rule("XD013", Severity.INFO, "missing-refs-metadata")
def _(ctx):
    for clue in ctx.parsed.clues:
        if _CROSSREF_RE.search(clue.body):
            if "refs" not in clue.metadata:
                yield finding("XD013", Severity.INFO, clue.line,
                              f"clue {clue.pos} references another clue "
                              f"but has no '^Refs:' metadata")


# ---------------------------------------------------------------------------
# Rules - info
# ---------------------------------------------------------------------------

@rule("XD201", Severity.INFO, "trailing-whitespace")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        if line and line != line.rstrip():
            yield finding("XD201", Severity.INFO, i, "trailing whitespace")


@rule("XD202", Severity.INFO, "headers-out-of-order")
def _(ctx):
    """Canonical headers appear out of conventional relative order. Doesn't
    care about non-canonical headers — they can interleave anywhere."""
    last_idx = -1
    for h in ctx.parsed.headers:
        k = h.key.lower()
        if k not in CANONICAL_HEADERS:
            continue
        idx = HEADER_ORDER.index(k)
        if idx < last_idx:
            yield finding("XD202", Severity.INFO, h.line,
                          f"header {h.key!r} appears out of conventional order")
        else:
            last_idx = idx


@rule("XD203", Severity.INFO, "leading-whitespace-on-grid")
def _(ctx):
    for row in ctx.parsed.grid:
        if row.line - 1 >= len(ctx.parsed.lines):
            continue
        raw = ctx.parsed.lines[row.line - 1]
        if raw and raw[0] in (" ", "\t"):
            yield finding("XD203", Severity.INFO, row.line,
                          "grid row has leading whitespace (legal but unnecessary)")


@rule("XD204", Severity.INFO, "tab-character")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        if "\t" in line:
            col = line.index("\t") + 1
            yield finding("XD204", Severity.INFO, i,
                          f"tab character at col {col}")


@rule("XD205", Severity.INFO, "limited-charset")
def _(ctx):
    """Grid uses 1 or 2 distinct letters. Catches redacted (all-X)
    contest puzzles and accidentally-corrupted imports."""
    if not ctx.parsed.grid:
        return
    distinct = set()
    for row in ctx.parsed.grid:
        for ch in row.cells:
            if ch in BLOCK_CHARS or ch == WILDCARD_CHAR:
                continue
            if ch.isalpha():
                distinct.add(ch.upper())
    if 1 <= len(distinct) <= 2:
        yield finding("XD205", Severity.INFO, ctx.parsed.grid[0].line,
                      f"grid uses only {len(distinct)} distinct letter(s) "
                      f"({sorted(distinct)}) — redacted? imported wrong?")


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


def _decode_with_findings(data: bytes):
    """Strict UTF-8 decode first; on failure, emit XD022 and fall back
    to replacement so the rest of the linter still gets to run."""
    try:
        return data.decode("utf-8"), []
    except UnicodeDecodeError as e:
        # Convert byte offset to (line, col) using the bad-bytes-replaced
        # text so the line number is still meaningful.
        text = data.decode("utf-8", errors="replace")
        line = data[:e.start].count(b"\n") + 1
        bad = data[e.start:e.end].hex()
        msg = (f"non-UTF-8 byte(s) at offset {e.start} (hex {bad}); "
               f"file decoded with U+FFFD replacement to allow further checks")
        return text, [Finding(code="XD022", severity=Severity.ERROR,
                              line=line, message=msg)]


def contexts_from_paths(paths):
    for path in iter_xd_paths(paths):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            print(f"{path}\tIO\terror reading: {e}", file=sys.stderr)
            continue
        text, decode_findings = _decode_with_findings(data)
        parsed = parse(text)
        parsed.parse_errors[:0] = decode_findings
        yield path, Ctx(filename=path, text=text, parsed=parsed)


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
        text, decode_findings = _decode_with_findings(content)
        parsed = parse(text)
        parsed.parse_errors[:0] = decode_findings
        yield path, Ctx(filename=path, text=text, parsed=parsed)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_checks(ctx: Ctx, active_codes):
    """Yield findings from the parser plus all active rules."""
    for f in ctx.parsed.parse_errors:
        if active_codes is None or f.code in active_codes:
            yield f
    for code, severity, _name, _experimental, fn in RULES:
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
    ap.add_argument("--no-experimental", action="store_true",
                    help="skip experimental rules (those interpreting "
                         "spec extensions like quantum/Schrödinger rebus)")
    args = ap.parse_args()

    if args.list_rules:
        print(f"{'CODE':<8} {'SEVERITY':<8} {'FLAGS':<7} NAME")
        for code, sev, name, experimental, _ in sorted(RULES):
            flags = "exp" if experimental else ""
            print(f"{code:<8} {sev.value:<8} {flags:<7} {name}")
        return 0

    experimental_codes = {code for (code, _s, _n, exp, _f) in RULES if exp}

    if args.enable_only:
        active = {c.strip() for c in args.enable_only.split(",") if c.strip()}
    elif args.disable:
        disabled = {c.strip() for c in args.disable.split(",") if c.strip()}
        active = {code for (code, _s, _n, _e, _f) in RULES} - disabled
        active |= {"XD901"} - disabled  # parse_errors stay enabled by default
    else:
        active = None

    if args.no_experimental:
        if active is None:
            active = {code for (code, _s, _n, _e, _f) in RULES} - experimental_codes
        else:
            active = active - experimental_codes

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
