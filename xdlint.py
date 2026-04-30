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
    xdlint.py --fix path                   apply mechanical fixes in place
    xdlint.py --fix --diff path            print unified diff, don't write

Severity gate:
    --max-severity {error,warning,info,debug}    default: warning
    Acts as both a print filter (findings below this level are suppressed)
    and an exit gate (exit 1 if any finding meets or exceeds the level).
    Use --max-severity info to surface feature-detection findings (XD3xx).

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
import difflib
import enum
import html
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
    DEBUG = "debug"

    @property
    def rank(self) -> int:
        return {"error": 4, "warning": 3, "info": 2, "debug": 1}[self.value]


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
    # Explicit-mode '## Foo' headers whose name isn't in EXPLICIT_SECTIONS.
    # Spec says ignore the section, but XD207 surfaces them so unexpected
    # sections (typos, tool-specific extensions) don't go unnoticed.
    unknown_sections: List[Tuple[int, str]] = field(default_factory=list)


@dataclass
class Ctx:
    filename: str
    text: str
    parsed: ParsedXd


# ---------------------------------------------------------------------------
# Parser - line-tracking; permissive about section structure
# ---------------------------------------------------------------------------
# Implicit-mode files lack '## Section' markers, so the parser identifies
# sections by content shape with a fallback to blank-line separators. When
# the spec separator (2+ blank lines) is missing, the parser recovers by
# auto-advancing the section and emits XD019 to flag the violation. This
# avoids a cascade where a single missing blank line turns into hundreds
# of downstream findings (XD001/XD002/XD004/...) about misclassified rows.

EXPLICIT_HEADER_RE = re.compile(r"^\s*##\s+([A-Za-z][A-Za-z0-9_-]*)")
EXPLICIT_SECTIONS = {"metadata": "metadata", "grid": "grid", "clues": "clues", "notes": "notes"}
CLUE_META_RE = re.compile(r"^([A-Za-z][\w-]*)\s+\^([A-Za-z][\w-]*)\s*:\s*(.*)$")
CLUE_POS_RE = re.compile(r"^([A-Za-z])(\d+)$")
_AUTO_CLUE_RE = re.compile(r"^[A-Za-z]?\d+\.\s")


def _looks_like_grid_row(stripped: str) -> bool:
    """Heuristic: stripped line whose every char is a letter, digit, block,
    or wildcard, with no internal whitespace. Used by the implicit-mode
    parser to detect when a missing blank-line separator has swallowed
    grid rows into the metadata section."""
    if not stripped or " " in stripped or "\t" in stripped:
        return False
    for c in stripped:
        if c.isalpha() or c.isdigit():
            continue
        if c in BLOCK_CHARS or c == WILDCARD_CHAR:
            continue
        return False
    return True


def _looks_like_clue(stripped: str) -> bool:
    return bool(_AUTO_CLUE_RE.match(stripped))


def _classify_line(line: str) -> str:
    """Coarse shape category used for implicit-mode auto-recovery.
    Order matters: clue check precedes header check because clue bodies
    may contain ':' (e.g. 'A1. Greeting: hi ~ HELLO')."""
    s = line.strip()
    if not s:
        return "blank"
    if EXPLICIT_HEADER_RE.match(line):
        return "explicit"
    if _looks_like_clue(s):
        return "clue"
    if ":" in s:
        return "header"
    if _looks_like_grid_row(s):
        return "grid"
    return "other"


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

    # Pass 2: classify each line for implicit-mode auto-recovery. Skipped
    # in explicit mode (markers handle section transitions explicitly).
    line_class = (
        [_classify_line(raw) for raw in lines]
        if section_mode == "implicit" else []
    )

    headers: List[Header] = []
    grid: List[GridRow] = []
    clues: List[Clue] = []
    notes_lines: List[str] = []
    unknown_sections: List[Tuple[int, str]] = []

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
                raw_name = m.group(1)
                name = raw_name.lower()
                if name in EXPLICIT_SECTIONS:
                    section = EXPLICIT_SECTIONS[name]
                    started = True
                    blank_run = 0
                    last_clue = None
                else:
                    # Per spec: unknown sections are ignored. Record the
                    # header line so XD207 can surface it.
                    section = "_unknown"
                    blank_run = 0
                    last_clue = None
                    unknown_sections.append((lineno, raw_name))
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

        # Implicit-mode auto-recovery: if the current line's shape doesn't
        # match the current section, advance the section and let the
        # dispatch below process the line in the right place. Only fires
        # in implicit mode (explicit '## Section' markers handle transitions
        # unambiguously). Emits XD019 to record the structural violation.
        if section_mode == "implicit":
            cls = line_class[lineno0]
            if section == "metadata" and cls == "grid":
                # Lookahead guards against single-word stray metadata lines:
                # only advance when the next non-blank line is also content
                # ('grid' confirms a real grid; 'clue' covers tiny puzzles
                # whose grid is a single row before clues start).
                future = [c for c in line_class[lineno0 + 1:] if c != "blank"]
                if future and future[0] in ("grid", "clue"):
                    parse_errors.append(Finding(
                        code="XD019", severity=Severity.WARNING, line=lineno,
                        message="line looks like a grid row; auto-advanced "
                                "to grid section (missing 2+ blank lines "
                                "between metadata and grid?)",
                    ))
                    section = "grid"
                    last_clue = None
            elif section == "grid" and cls == "clue":
                parse_errors.append(Finding(
                    code="XD019", severity=Severity.WARNING, line=lineno,
                    message="line looks like a clue; auto-advanced to "
                            "clues section (missing 2+ blank lines "
                            "between grid and clues?)",
                ))
                section = "clues"
                last_clue = None

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
            if mm:
                pos_ref = mm.group(1)
                if last_clue is not None and pos_ref == last_clue.pos:
                    _, mkey, mval = mm.groups()
                    last_clue.metadata[mkey.lower()] = mval.strip()
                    continue
                # Looks like metadata but isn't anchored to the preceding
                # clue. Per spec, '^Key:' lines attach to the clue immediately
                # above. Emit XD021 and skip the line.
                if last_clue is None:
                    msg = (f"clue metadata for {pos_ref!r} appears with no "
                           f"preceding clue")
                else:
                    msg = (f"clue metadata for {pos_ref!r} doesn't follow "
                           f"its referent (preceding clue is "
                           f"{last_clue.pos!r})")
                parse_errors.append(Finding(
                    code="XD021", severity=Severity.ERROR,
                    line=lineno, message=msg,
                ))
                continue
            # Normal clue: "A1. Body ~ ANSWER". Prefer the spec separator
            # ' ~ '; fall back to a bare '~' only when no spaced form is
            # present, so a clue body containing '~' (math, ASCII art) still
            # parses with the trailing answer correctly identified.
            spaced_idx = stripped.rfind(" ~ ")
            if spaced_idx > 0:
                head_part = stripped[:spaced_idx]
                answer = stripped[spaced_idx + 3:].strip()
            else:
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

        elif section == "notes":
            notes_lines.append(stripped)
        # else: section == "_unknown" — per spec, ignored entirely.

    return ParsedXd(
        text=text, lines=lines, section_mode=section_mode,
        headers=headers, grid=grid, clues=clues,
        notes_text="\n".join(notes_lines), parse_errors=parse_errors,
        unknown_sections=unknown_sections,
    )


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

RuleFn = Callable[[Ctx], Iterator[Finding]]
RULES: List[tuple] = []  # (code, severity, name, experimental, fn)

# Findings emitted directly by the parser (not via @rule). Listed here so
# --list-rules surfaces them. The actual emission sites are inside parse()
# and the file-decode helpers; severity/message there must match what's
# documented here.
PARSER_LEVEL_FINDINGS: List[tuple] = [
    ("XD012", Severity.ERROR,   "embedded-newline-in-clue"),
    ("XD019", Severity.WARNING, "missing-section-separator"),
    ("XD021", Severity.ERROR,   "misplaced-clue-metadata"),
    ("XD022", Severity.ERROR,   "non-utf8-bytes"),
]


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
            # Otherwise match one of the chosen direction's alts. Try the
            # longer alt first: with unequal-length alts (e.g. 1=A|AB), a
            # greedy short match would consume the wrong number of cells
            # and force the next cell into a false XD007.
            matched = False
            for alt in sorted(chosen, key=len, reverse=True):
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
    position, so counting positions rather than clues handles that.

    Only counts A/D clues: cluegroup positions ('X1.' etc.) don't map to
    slots in `idx`, and a single XD017-malformed clue shouldn't suppress
    the count check for the rest of the file."""
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    n_slots = len(idx)
    n_positions = len({c.pos for c in ctx.parsed.clues
                       if c.pos and c.direction in ("A", "D")})
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

# Source-encoding candidates for each C1 codepoint. cp1252 covers most of our
# corpus (em dashes, smart quotes, š); some files were originally Mac Roman
# (0x8E='é' in Mac Roman, 'Ž' in cp1252); a few older Newsday/NYSun files
# came from cp437/cp850 (DOS) where 0x82='é', 0x89='ë'; and U+0080/U+0098
# sometimes stand for symbols (°, ÷) that no standard encoding maps to.
# Showing all three lets the user pick when --fix can't decide.
_CP1252_CANDIDATES = {}
_MAC_ROMAN_CANDIDATES = {}
_CP437_CANDIDATES = {}
for _b in range(0x80, 0xa0):
    try:
        _CP1252_CANDIDATES[_b] = bytes([_b]).decode("cp1252")
    except UnicodeDecodeError:
        pass
    _MAC_ROMAN_CANDIDATES[_b] = bytes([_b]).decode("mac_roman")
    _CP437_CANDIDATES[_b] = bytes([_b]).decode("cp437")


def _c1_candidates(cp: int) -> str:
    cp1252 = (f"cp1252: {_CP1252_CANDIDATES[cp]!r}"
              if cp in _CP1252_CANDIDATES else "cp1252: undefined")
    mac = f"Mac Roman: {_MAC_ROMAN_CANDIDATES[cp]!r}"
    cp437 = f"cp437: {_CP437_CANDIDATES[cp]!r}"
    return f"{cp1252}, {mac}, {cp437}"


@rule("XD010", Severity.ERROR, "bad-codepoint")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        m = _C1_RE.search(line)
        if m:
            cp = ord(m.group(0))
            yield finding("XD010", Severity.ERROR, i,
                          f"C1 control U+{cp:04X} at col {m.start() + 1} "
                          f"({_c1_candidates(cp)})")


# UTF-8 byte sequence \xc2\xXX or \xc3\xXX (latin-supplement block) misread
# as latin-1 leaves 'Â' or 'Ã' followed by a U+0080-U+00BF char. Re-encoding
# as latin-1 and decoding as UTF-8 reverses the corruption.
_LATIN1_UTF8_RE = re.compile(r"[\xc2\xc3][\x80-\xbf]")


@rule("XD009", Severity.ERROR, "latin1-utf8-mojibake")
def _(ctx):
    """UTF-8 latin-supplement bytes misread as latin-1 (e.g. 'Ãª' for 'ê',
    'Ã©' for 'é'). Common when a UTF-8 .puz file was decoded as ISO-8859-1
    by an upstream converter."""
    for i, line in enumerate(ctx.parsed.lines, 1):
        for m in _LATIN1_UTF8_RE.finditer(line):
            try:
                fix = m.group(0).encode('latin-1').decode('utf-8')
            except UnicodeDecodeError:
                continue
            yield finding("XD009", Severity.ERROR, i,
                          f"latin-1 misread of UTF-8 {m.group(0)!r} "
                          f"at col {m.start() + 1} (should be {fix!r})")


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


@rule("XD701", Severity.WARNING, "filename-date-mismatch")
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
        yield finding("XD701", Severity.WARNING, line,
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


@rule("XD018", Severity.DEBUG, "multiple-tilde-separators")
def _(ctx):
    """A clue line with more than one ' ~ ' (tilde with spaces both
    sides — the spec separator). Parsers may disagree on which is the
    answer divider. A single tilde without surrounding spaces inside
    clue text is legal and not flagged."""
    for clue in ctx.parsed.clues:
        if clue.raw.count(" ~ ") > 1:
            yield finding("XD018", Severity.DEBUG, clue.line,
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

@rule("XD101", Severity.DEBUG, "backslash-in-clue")
def _(ctx):
    """Backslashes in clue bodies were sometimes import bugs in the
    early corpus, but in practice flagging them produces too many
    false positives (legitimate uses include emoticons, file paths,
    LaTeX-ish notation). Kept as DEBUG so it can still be surfaced
    on demand."""
    for clue in ctx.parsed.clues:
        if "\\" in clue.body:
            # clue.raw is the stripped form, so its offsets are wrong if the
            # source line had any leading whitespace. Use the original line.
            original = ctx.parsed.lines[clue.line - 1]
            col = original.find("\\") + 1
            yield finding("XD101", Severity.DEBUG, clue.line,
                          f"backslash at col {col} (possible import artifact)")


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


@rule("XD103", Severity.INFO, "editor-folded-into-author")
def _(ctx):
    """Author header value carries editor info ('Smith / Ed. Jones',
    'Smith; edited by Jones'). Split-out via --fix is available but
    optional — the spec does not require a separate Editor header."""
    for h in ctx.parsed.headers:
        if h.key.lower() != "author":
            continue
        if _AUTHOR_EDITOR_RE.search(h.value):
            yield finding("XD103", Severity.INFO, h.line,
                          "Author value contains editor info; "
                          "--fix can split into separate Author and Editor headers")


# Canonical metadata header keys, in conventional ordering. Source of
# truth: xdfile.HEADER_ORDER.
HEADER_ORDER = [
    "title", "author", "editor", "copyright", "number", "date",
    "relation", "special", "rebus", "cluegroup", "description", "notes",
]
CANONICAL_HEADERS = set(HEADER_ORDER)


@rule("XD104", Severity.WARNING, "non-standard-special-value")
def _(ctx):
    """Spec defines exactly two Special values: 'shaded' or 'circle'.
    Empty values, typos ('cirlce'), and tool-specific extensions all land
    here; empty is special-cased in the message because that's the most
    common form."""
    valid = {"shaded", "circle"}
    for h in ctx.parsed.headers:
        if h.key.lower() != "special":
            continue
        v = h.value.strip()
        if not v:
            yield finding("XD104", Severity.WARNING, h.line,
                          "Special header is empty (spec values: "
                          "'shaded' or 'circle')")
        elif v.lower() not in valid:
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


@rule("XD106", Severity.WARNING, "missing-date")
def _(ctx):
    """Date is practically required. Split out from XD108 (missing Title)
    so that the --fix path (which can sometimes infer Date from the
    filename) has its own targetable rule code."""
    if not any(h.key.lower() == "date" for h in ctx.parsed.headers):
        yield finding("XD106", Severity.WARNING, 0,
                      "missing recommended header 'Date'")


@rule("XD108", Severity.WARNING, "missing-title")
def _(ctx):
    """Title is practically required. No fixer — there's no reliable
    signal to infer a title from. Author is also recommended but is
    flagged separately (XD103) when present-but-messy."""
    if not any(h.key.lower() == "title" for h in ctx.parsed.headers):
        yield finding("XD108", Severity.WARNING, 0,
                      "missing recommended header 'Title'")


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


@rule("XD111", Severity.INFO, "non-canonical-header-key")
def _(ctx):
    """Header key isn't one of the spec-canonical ones. Catches typos
    ('Note' instead of 'Notes') and tool-specific extensions. Spec says
    additional headers are 'allowed but ignored', so this is informational
    only — surfacing the keys lets the corpus-wide audit see what
    extensions are in use without forcing a fix."""
    for h in ctx.parsed.headers:
        if h.key.lower() not in CANONICAL_HEADERS:
            yield finding("XD111", Severity.INFO, h.line,
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
# Rules - feature detection (informational; one finding per file per feature)
# ---------------------------------------------------------------------------
# These announce that a file uses a particular spec feature so the corpus
# can be searched for examples (`xdlint.py --max-severity info corpus/ |
# grep XD3xx`). They never indicate a problem; they're just signals.

@rule("XD301", Severity.INFO, "uses-rebus")
def _(ctx):
    """File declares a Rebus header with at least one valid expansion."""
    rebus = parse_rebus_header(get_header(ctx.parsed, "Rebus") or "")
    if not rebus:
        return
    line = next((h.line for h in ctx.parsed.headers
                 if h.key.lower() == "rebus"), 0)
    yield finding("XD301", Severity.INFO, line,
                  f"uses Rebus feature ({len(rebus)} key(s): "
                  f"{sorted(rebus)})")


@rule("XD302", Severity.INFO, "uses-special")
def _(ctx):
    """File declares a Special header (shaded/circle cells)."""
    for h in ctx.parsed.headers:
        if h.key.lower() == "special":
            yield finding("XD302", Severity.INFO, h.line,
                          f"uses Special feature (value={h.value!r})")
            break


@rule("XD303", Severity.INFO, "uses-clue-metadata")
def _(ctx):
    """At least one clue carries '^Key: value' metadata."""
    for clue in ctx.parsed.clues:
        if clue.metadata:
            keys = sorted(clue.metadata)
            yield finding("XD303", Severity.INFO, clue.line,
                          f"uses clue-metadata feature "
                          f"(first at {clue.pos}, keys: {keys})")
            break


# Spec markup forms: {/italic/}, {*bold*}, {_underscore_}, {-strike-}.
_CLUE_MARKUP_RE = re.compile(r"\{[/*_-][^/*_\-{}]+[/*_-]\}")


@rule("XD304", Severity.INFO, "uses-clue-markup")
def _(ctx):
    """At least one clue body uses the spec's inline markup syntax."""
    for clue in ctx.parsed.clues:
        m = _CLUE_MARKUP_RE.search(clue.body)
        if m:
            yield finding("XD304", Severity.INFO, clue.line,
                          f"uses clue-markup feature "
                          f"(first at {clue.pos}: {m.group(0)!r})")
            break


@rule("XD305", Severity.INFO, "uses-cluegroup")
def _(ctx):
    """File declares a Cluegroup header or has clues in a non-A/D group."""
    cg = next((h for h in ctx.parsed.headers
               if h.key.lower() == "cluegroup"), None)
    if cg is not None:
        yield finding("XD305", Severity.INFO, cg.line,
                      f"uses Cluegroup feature (value={cg.value!r})")
        return
    for clue in ctx.parsed.clues:
        if clue.direction and clue.direction not in ("A", "D"):
            yield finding("XD305", Severity.INFO, clue.line,
                          f"uses Cluegroup feature "
                          f"(undeclared group {clue.direction!r} "
                          f"at {clue.pos})")
            break


@rule("XD306", Severity.INFO, "uses-quantum-rebus")
def _(ctx):
    """File uses the (extension) quantum/Schrödinger rebus syntax: '/'
    for directional alts or '|' for letter-choice alts."""
    rebus = parse_rebus_header(get_header(ctx.parsed, "Rebus") or "")
    for k, exp in rebus.items():
        if exp.is_directional or exp.is_schrodinger(0) or exp.is_schrodinger(1):
            line = next((h.line for h in ctx.parsed.headers
                         if h.key.lower() == "rebus"), 0)
            kind = ("directional" if exp.is_directional
                    else "Schrödinger")
            yield finding("XD306", Severity.INFO, line,
                          f"uses quantum-rebus feature ({kind} key {k!r})")
            break


@rule("XD307", Severity.INFO, "uses-notes-section")
def _(ctx):
    """File has content in the Notes section."""
    if ctx.parsed.notes_text.strip():
        yield finding("XD307", Severity.INFO, 0,
                      "uses Notes section")


@rule("XD308", Severity.INFO, "uses-open-cells")
def _(ctx):
    """Grid uses '_' for non-cell positions (non-rectangular puzzle shapes)."""
    for row in ctx.parsed.grid:
        col = row.cells.find("_")
        if col == -1:
            col = row.cells.find("＿")
        if col != -1:
            yield finding("XD308", Severity.INFO, row.line,
                          f"uses open-cell feature ('_' at col {col})")
            break


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


@rule("XD204", Severity.WARNING, "tab-character")
def _(ctx):
    for i, line in enumerate(ctx.parsed.lines, 1):
        if "\t" in line:
            col = line.index("\t") + 1
            yield finding("XD204", Severity.WARNING, i,
                          f"tab character at col {col}")


@rule("XD205", Severity.WARNING, "limited-charset")
def _(ctx):
    """Grid uses 1 or 2 distinct letters. Catches redacted (all-X)
    contest puzzles and accidentally-corrupted imports — almost always
    one of those, never legitimate, so warn-level."""
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
        yield finding("XD205", Severity.WARNING, ctx.parsed.grid[0].line,
                      f"grid uses only {len(distinct)} distinct letter(s) "
                      f"({sorted(distinct)}) — redacted? imported wrong?")


# The spec mentions only 'Refs:' as a clue-metadata key, while explicitly
# leaving the namespace open. Other tools (e.g. xd-crossword-tools) have
# adopted further keys like 'Hint:' and 'Alt:'/'Alt1:'..'Alt9:' for
# Schrödinger puzzles, but those aren't in the spec; surfacing them as
# unrecognized is intentional, pending a spec discussion.
RECOGNIZED_CLUE_META_KEYS = {"refs"}


@rule("XD206", Severity.INFO, "unrecognized-clue-metadata-key")
def _(ctx):
    """Clue carries '^Key:' metadata with a key not in the spec. The spec
    mentions only 'Refs:' but leaves the namespace open, so this is
    informational, not a violation. Useful for catching typos ('Reffs:',
    'Hnt:') and surfacing tool-specific extensions."""
    seen = set()
    for clue in ctx.parsed.clues:
        for key in clue.metadata:
            if key in RECOGNIZED_CLUE_META_KEYS:
                continue
            if (clue.line, key) in seen:
                continue
            seen.add((clue.line, key))
            yield finding("XD206", Severity.INFO, clue.line,
                          f"clue {clue.pos} has unrecognized metadata key "
                          f"{key!r} (spec recognizes only "
                          f"{sorted(RECOGNIZED_CLUE_META_KEYS)})")


@rule("XD207", Severity.INFO, "unknown-section")
def _(ctx):
    """Explicit-mode '## Foo' header whose name isn't one of the spec
    sections (metadata/grid/clues/notes). Spec says ignore the section,
    but a typo or tool-specific extension shouldn't disappear silently."""
    known = sorted(EXPLICIT_SECTIONS)
    for line, name in ctx.parsed.unknown_sections:
        yield finding("XD207", Severity.INFO, line,
                      f"unknown section '## {name}' (spec sections: "
                      f"{known}); content ignored")


# ---------------------------------------------------------------------------
# Fixers - mechanical corrections for safe rules
# ---------------------------------------------------------------------------
# A fixer takes the file text and returns (new_text, n_fixes). Fixers that
# need structural data re-parse internally so the pipeline can run them in
# sequence without an external coordinator. Each tier-1 fixer is idempotent;
# running it twice on its own output makes no further changes.

FixerFn = Callable[[str], Tuple[str, int]]
FIXERS: Dict[str, Tuple[bool, FixerFn]] = {}  # code -> (unsafe, fn)

# Apply order matters when fixers interact: encoding first (changes which
# chars later passes see), then whitespace/structural cleanup, then
# header reordering, then in-section content fixes.
FIX_ORDER = [
    "XD009",  # UTF-8 latin-supplement misread as latin-1 ('Ãª' -> 'ê').
              # Runs before XD010 because a triple-mojibake like
              # 'Â' decomposes to 'Â' + '' here,
              # leaving '' which the XD010 trailer pass then
              # reconstructs to '"'.
    "XD010",  # cp1252 mojibake -> intended chars
    "XD011",  # HTML entities -> unescaped chars
    "XD110",  # de-indent '## Section' headers
    "XD203",  # de-indent grid rows
    "XD204",  # tabs -> spaces
    "XD201",  # trim trailing whitespace
    "XD103",  # split editor out of Author header
    "XD107",  # drop duplicate header lines (after XD103: lets XD103 pick the
              # editor-bearing Author even if it isn't the first one, then
              # cleans up the duplicate it leaves behind)
    "XD202",  # reorder canonical headers (picks up the new Editor)
    "XD102",  # collapse 2+ blank lines in clues to 1
    "XD013",  # synthesize ^Refs from cross-refs in clue bodies
]


def fixer(code: str, unsafe: bool = False):
    def deco(fn: FixerFn) -> FixerFn:
        FIXERS[code] = (unsafe, fn)
        return fn
    return deco


def _detect_nl(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


# U+008E is the only codepoint where cp1252's mapping is consistently wrong
# in our corpus: cp1252 says 'Ž' (Slavic), but every U+008E we have is the
# Mac Roman 'é' (Cézanne, José, risqué, Gérard, Cité, entrée). Override.
_CP1252_OVERRIDES = {chr(0x8e): "é"}

# Single-byte C1 controls we refuse to auto-fix because cp1252 maps them
# to a character (€, ˜) that almost never matches the intent in our corpus
# (degree sign, division sign, etc.). The XD010 finding shows candidates
# so the user can fix manually. Only applies to standalone occurrences;
# U+0080 followed by another C1 control is handled by the UTF-8 trailer
# pass below.
_CP1252_SKIP_SINGLE = {chr(0x80), chr(0x98)}

# Two consecutive C1 controls beginning with U+0080 are almost always the
# trailing two bytes of a UTF-8 sequence \xe2\x80\xXX (the smart-quote /
# dash / bullet block U+2010-U+201F). The lead byte may have been dropped
# (we prepend \xe2) or survived as 'â' (the latin-1 reading of \xe2, after
# a UTF-8 round-trip). Either way, latin-1-encoding the run and
# UTF-8-decoding it reconstructs the original character.
_UTF8_TRAILER_RE = re.compile(r"â?\x80[\x80-\x9f]")

# Orphan smart-quote trailer: U+009C / U+009D appearing immediately after a
# straight ". The original was the UTF-8 byte sequence \xe2\x80\x9c (left
# curly) or \xe2\x80\x9d (right curly). Some upstream processor replaced the
# \xe2\x80 with a straight " quote but left the \x9c/\x9d trailer behind.
# The straight " already serves as the quote; the trailer is dead weight.
# In our corpus this pattern is 100% uniform — every U+009C/U+009D is
# preceded by ", with no exceptions.
_ORPHAN_QUOTE_TRAILER_RE = re.compile(r'"[\x9c\x9d]')


@fixer("XD009")
def _(text):
    """UTF-8 latin-supplement misread as latin-1: 'Ã' + cont-byte (and 'Â'
    + cont-byte) re-decoded through latin-1 -> UTF-8 round-trip."""
    count = 0
    def repl(m):
        nonlocal count
        try:
            replacement = m.group(0).encode('latin-1').decode('utf-8')
        except UnicodeDecodeError:
            return m.group(0)
        count += 1
        return replacement
    return _LATIN1_UTF8_RE.sub(repl, text), count


@fixer("XD010")
def _(text):
    """C1-control mojibake. Four passes:

    1. UTF-8 trailer: an optional 'â' + \\u0080 + another C1 control ->
       reconstructed UTF-8 smart quote / dash (handles bytes whose lead
       \\xe2 was either lost or survived as latin-1 'â').
    2. Orphan smart-quote trailer: a U+009C/U+009D after a straight " is
       a stray byte from a UTF-8 smart quote whose lead bytes were turned
       into the straight ". Drop the trailer byte.
    3. Per-codepoint overrides where cp1252 is reliably wrong (U+008E -> é).
    4. cp1252 default for the rest, skipping codepoints that are too
       ambiguous to auto-fix (U+0080, U+0098).
    """
    count = 0

    def utf8_repl(m):
        nonlocal count
        s = m.group(0)
        bs = s.encode("latin-1")
        if not bs.startswith(b"\xe2"):
            bs = b"\xe2" + bs
        try:
            replacement = bs.decode("utf-8")
        except UnicodeDecodeError:
            return s
        count += 1
        return replacement
    text = _UTF8_TRAILER_RE.sub(utf8_repl, text)

    def orphan_repl(m):
        nonlocal count
        count += 1
        return '"'
    text = _ORPHAN_QUOTE_TRAILER_RE.sub(orphan_repl, text)

    def repl(m):
        nonlocal count
        ch = m.group(0)
        if ch in _CP1252_OVERRIDES:
            count += 1
            return _CP1252_OVERRIDES[ch]
        if ch in _CP1252_SKIP_SINGLE:
            return ch
        try:
            replacement = ch.encode("latin-1").decode("cp1252")
        except UnicodeDecodeError:
            # cp1252 leaves 5 byte slots undefined; leave those alone.
            return ch
        count += 1
        return replacement
    return _C1_RE.sub(repl, text), count


@fixer("XD011")
def _(text):
    count = 0
    def repl(m):
        nonlocal count
        s = m.group(0)
        out = html.unescape(s)
        if out != s:
            count += 1
        return out
    return _HTML_ENTITY_RE.sub(repl, text), count


@fixer("XD110")
def _(text):
    count = 0
    out = []
    for line in text.splitlines(keepends=True):
        if _INDENTED_HEADER_RE.match(line):
            count += 1
            out.append(line.lstrip(" \t"))
        else:
            out.append(line)
    return "".join(out), count


@fixer("XD203")
def _(text):
    parsed = parse(text)
    if not parsed.grid:
        return text, 0
    grid_lines = {row.line for row in parsed.grid}
    count = 0
    out = []
    for i, line in enumerate(text.splitlines(keepends=True), 1):
        if i in grid_lines and line[:1] in (" ", "\t"):
            count += 1
            out.append(line.lstrip(" \t"))
        else:
            out.append(line)
    return "".join(out), count


@fixer("XD204")
def _(text):
    if "\t" not in text:
        return text, 0
    count = sum(1 for line in text.splitlines() if "\t" in line)
    return text.replace("\t", " "), count


@fixer("XD201")
def _(text):
    count = 0
    out = []
    for line in text.splitlines(keepends=True):
        if line.endswith("\r\n"):
            new = line[:-2].rstrip(" \t") + "\r\n"
        elif line.endswith("\n"):
            new = line[:-1].rstrip(" \t") + "\n"
        else:
            new = line.rstrip(" \t")
        if new != line:
            count += 1
        out.append(new)
    return "".join(out), count


@fixer("XD107")
def _(text):
    parsed = parse(text)
    seen = set()
    drops = set()
    for h in parsed.headers:
        k = h.key.lower()
        if k in seen:
            drops.add(h.line)
        else:
            seen.add(k)
    if not drops:
        return text, 0
    lines = text.splitlines(keepends=True)
    out = [line for i, line in enumerate(lines, 1) if i not in drops]
    return "".join(out), len(drops)


# Port of clean_author() from scripts/21-clean-metadata.py. Splits an Author
# value that looks like "Smith / Ed. Jones" or "Smith; edited by Jones" into
# (author, editor). Empty-author cases (e.g. "Edited by Smith") get returned
# as ("", "Smith"); the fixer below treats those as out-of-scope.
_CLEAN_AUTHOR_RE = re.compile(
    r"(?i)(?:(?:By )*(.+)(?:[;/,-]|and) *)?"
    r"(?:edited|Editor|(?<!\w)Ed[.])(?: By)*(.*)"
)


def _clean_author(author: str, editor: str) -> Tuple[str, str]:
    if author:
        m = _CLEAN_AUTHOR_RE.search(author)
        if m:
            author, editor = m.groups()
        if author:
            while author.lower().startswith("by "):
                author = author[3:]
            while author and author[-1] in ",.":
                author = author[:-1]
        else:
            author = ""
        if " / " in author and not editor:
            author, editor = author.rsplit(" / ", 1)
    if editor:
        while editor.lower().startswith("by "):
            editor = editor[3:]
        while editor and editor[-1] in ",.":
            editor = editor[:-1]
    return (author or "").strip(), (editor or "").strip()


@fixer("XD103")
def _(text):
    """Split 'Author: X / Ed. Y' style values into separate Author and
    Editor headers. Conservative: skipped when the cleaned Author would be
    empty (e.g. 'Edited by Smith' — a content reinterpretation we don't
    apply silently) or when an Editor header already exists with content
    that the split would overwrite differently."""
    parsed = parse(text)
    # Pick the first Author whose value carries editor info — handles the
    # rare case where there are duplicate Author lines and the dirty one
    # isn't first. We delete sibling Author lines ourselves rather than
    # leaving them for XD107: XD107 keeps the *first* duplicate, which
    # would discard the cleaned Author when the dirty one wasn't first.
    author_h = next((h for h in parsed.headers
                     if h.key.lower() == "author"
                     and _AUTHOR_EDITOR_RE.search(h.value)), None)
    editor_h = next((h for h in parsed.headers
                     if h.key.lower() == "editor"), None)
    if author_h is None:
        return text, 0
    current_editor = editor_h.value if editor_h else ""
    new_author, new_editor = _clean_author(author_h.value, current_editor)
    if not new_author:
        return text, 0
    sibling_author_lines = {h.line for h in parsed.headers
                            if h.key.lower() == "author"
                            and h.line != author_h.line}
    if (new_author == author_h.value and new_editor == current_editor
            and not sibling_author_lines):
        return text, 0
    # Don't clobber a non-empty existing Editor with a different value.
    if editor_h and current_editor and new_editor != current_editor:
        return text, 0

    lines = text.splitlines(keepends=True)
    nl = _detect_nl(text)
    fixes = 0

    def _line_nl(s: str) -> str:
        if s.endswith("\r\n"):
            return "\r\n"
        if s.endswith("\n"):
            return "\n"
        return ""

    a_idx = author_h.line - 1
    a_orig = lines[a_idx]
    new_a_line = f"{author_h.key}: {new_author}{_line_nl(a_orig)}"
    if new_a_line != a_orig:
        lines[a_idx] = new_a_line
        fixes += 1

    inserted_after = None  # 1-indexed line we inserted after, if any
    if new_editor != current_editor:
        if editor_h is not None:
            e_idx = editor_h.line - 1
            e_orig = lines[e_idx]
            new_e_line = f"{editor_h.key}: {new_editor}{_line_nl(e_orig)}"
            if new_e_line != e_orig:
                lines[e_idx] = new_e_line
                fixes += 1
        elif new_editor:
            lines.insert(a_idx + 1, f"Editor: {new_editor}{nl}")
            inserted_after = author_h.line
            fixes += 1

    # Drop sibling Author lines now (after the rewrite/insert above) so
    # XD107 doesn't have a chance to keep the wrong one. Walk highest-first
    # so earlier deletions don't shift later indices.
    for sib_line in sorted(sibling_author_lines, reverse=True):
        sib_idx = sib_line - 1
        if inserted_after is not None and sib_line > inserted_after:
            sib_idx += 1
        del lines[sib_idx]
        fixes += 1

    return "".join(lines), fixes


@fixer("XD202")
def _(text):
    # Side effect to be aware of: when this fixer runs, every relocated
    # canonical header line gets rewritten as f"{key}: {value}{nl}", which
    # silently normalizes any non-canonical spacing (extra spaces after the
    # colon, etc.) on those lines even though the user's lint trigger was
    # only about ordering. Acceptable in practice since the normalized form
    # is the spec form, but worth knowing when reading a fix diff.
    parsed = parse(text)
    canonical = [h for h in parsed.headers if h.key.lower() in CANONICAL_HEADERS]
    if not canonical:
        return text, 0
    keys_in_order = [h.key.lower() for h in canonical]
    target = sorted(keys_in_order, key=HEADER_ORDER.index)
    if keys_in_order == target:
        return text, 0
    sorted_headers = sorted(canonical, key=lambda h: HEADER_ORDER.index(h.key.lower()))
    canonical_slots = sorted(h.line - 1 for h in canonical)
    lines = text.splitlines(keepends=True)
    moves = 0
    for slot, h in zip(canonical_slots, sorted_headers):
        original = lines[slot]
        if original.endswith("\r\n"):
            nl = "\r\n"
        elif original.endswith("\n"):
            nl = "\n"
        else:
            nl = ""
        new_line = f"{h.key}: {h.value}{nl}"
        if new_line != original:
            moves += 1
        lines[slot] = new_line
    return "".join(lines), moves


@fixer("XD102")
def _(text):
    parsed = parse(text)
    if not parsed.clues:
        return text, 0
    first = parsed.clues[0].line
    last = parsed.clues[-1].line
    out = []
    blank_run = 0
    fixes = 0
    counted_run = False
    for i, line in enumerate(text.splitlines(keepends=True), 1):
        in_clues = first <= i <= last
        is_blank = not line.strip()
        if in_clues and is_blank:
            blank_run += 1
            if blank_run == 1:
                out.append(line)
                counted_run = False
            else:
                # 2+ blanks: keep only the first; XD102 fires once per run.
                if not counted_run:
                    fixes += 1
                    counted_run = True
        else:
            blank_run = 0
            counted_run = False
            out.append(line)
    return "".join(out), fixes


@fixer("XD013")
def _(text):
    parsed = parse(text)
    if not parsed.clues:
        return text, 0
    cross_re = re.compile(r"\b(\d+)[-\s]([Aa]cross|[Dd]own)\b")
    insertions: List[Tuple[int, str]] = []
    for clue in parsed.clues:
        if "refs" in clue.metadata:
            continue
        # Skip uniclue (numeric-only pos) — '5 ^Refs:' won't match the
        # spec metadata regex, which requires a leading letter.
        if not clue.pos or not clue.pos[0].isalpha():
            continue
        seen = set()
        refs = []
        for m in cross_re.finditer(clue.body):
            num = m.group(1)
            direction = "A" if m.group(2)[0].lower() == "a" else "D"
            r = f"{direction}{num}"
            if r not in seen:
                seen.add(r)
                refs.append(r)
        if refs:
            insertions.append((clue.line, f"{clue.pos} ^Refs: {' '.join(refs)}"))
    if not insertions:
        return text, 0
    nl = _detect_nl(text)
    lines = text.splitlines(keepends=True)
    for line_no, content in reversed(insertions):
        idx = line_no - 1
        if 0 <= idx < len(lines) and not lines[idx].endswith("\n"):
            lines[idx] = lines[idx] + nl
        lines.insert(line_no, content + nl)
    return "".join(lines), len(insertions)


def apply_fixes(text: str, codes: Optional[set],
                unsafe_ok: bool) -> Tuple[str, Dict[str, int]]:
    """Apply fixers in canonical order. Each fixer is idempotent and
    reparses internally if needed, so a single pass is sufficient."""
    counts: Dict[str, int] = {}
    for code in FIX_ORDER:
        if codes is not None and code not in codes:
            continue
        if code not in FIXERS:
            continue
        unsafe, fn = FIXERS[code]
        if unsafe and not unsafe_ok:
            continue
        new_text, n = fn(text)
        if new_text != text:
            counts[code] = counts.get(code, 0) + n
            text = new_text
    return text, counts


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
        # UnicodeDecodeError carries only the first bad span. Any further
        # bad bytes were silently turned into U+FFFD by the replace decode
        # — call that out so users don't trust this finding as the only
        # encoding issue in the file.
        msg = (f"non-UTF-8 byte(s) at offset {e.start} (hex {bad}); "
               f"file decoded with U+FFFD replacement to allow further "
               f"checks (additional bad bytes elsewhere may be silently "
               f"replaced)")
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


def _run_fix_mode(args, source, active_codes):
    """Apply fixers per file, then re-lint and report what's left.
    With --diff, print diffs to stdout and skip writing."""
    fix_codes = set(FIXERS.keys())
    if active_codes is not None:
        fix_codes &= active_codes

    files_seen = 0
    files_changed = 0
    total_fixes = 0
    findings_total = 0
    gate_hit = 0
    gate_rank = Severity(args.max_severity).rank

    for path, ctx in source:
        files_seen += 1

        # If the file has decode errors, skip — the in-memory text already
        # has U+FFFD replacements and writing it back would lose bytes.
        if any(f.code == "XD022" for f in ctx.parsed.parse_errors):
            print(f"{path}\tinfo\tskip\tnot fixing: file has non-UTF-8 bytes",
                  file=sys.stderr)
            _SLOT_CACHE.pop(id(ctx), None)
            continue

        new_text, counts = apply_fixes(ctx.text, fix_codes, args.unsafe_fixes)
        changed = new_text != ctx.text

        if changed:
            files_changed += 1
            total_fixes += sum(counts.values())
            if args.diff:
                diff = "".join(difflib.unified_diff(
                    ctx.text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=path, tofile=path, n=3,
                ))
                sys.stdout.write(diff)
            else:
                with open(path, "wb") as f:
                    f.write(new_text.encode("utf-8"))
            if args.show_fixes:
                msg = ", ".join(f"{c}x{n}" for c, n in sorted(counts.items()))
                print(f"{path}: {msg}", file=sys.stderr)

        # In write mode, surface remaining findings (after fixes).
        # In --diff mode, suppress per ruff's fix-only semantics.
        if not args.diff:
            if changed:
                fixed_parsed = parse(new_text)
                fixed_ctx = Ctx(filename=path, text=new_text, parsed=fixed_parsed)
            else:
                fixed_ctx = ctx
            for f in run_checks(fixed_ctx, active_codes):
                if f.severity.rank < gate_rank:
                    continue
                print(format_finding(path, f))
                findings_total += 1
                if f.severity.rank >= gate_rank:
                    gate_hit += 1
            _SLOT_CACHE.pop(id(fixed_ctx), None)

        _SLOT_CACHE.pop(id(ctx), None)

    if args.diff:
        print(f"\n{files_changed} of {files_seen} file(s) would be modified",
              file=sys.stderr)
        return 1 if files_changed > 0 else 0

    print(f"\nfixed {total_fixes} issue(s) in {files_changed} of "
          f"{files_seen} file(s); {findings_total} remaining finding(s), "
          f"{gate_hit} at or above '{args.max_severity}'", file=sys.stderr)
    return 1 if gate_hit > 0 else 0


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
                    choices=["error", "warning", "info", "debug"],
                    default="warning",
                    help="threshold for both printing and the exit gate: "
                         "findings below this level are suppressed, and "
                         "exit is nonzero if any finding meets or exceeds "
                         "this level (default: warning)")
    ap.add_argument("--disable", default="",
                    help="comma-separated rule codes to skip (e.g. XD013,XD016)")
    ap.add_argument("--enable-only", default="",
                    help="comma-separated rule codes to run (overrides --disable)")
    ap.add_argument("--list-rules", action="store_true",
                    help="print the rule catalog and exit")
    ap.add_argument("--no-experimental", action="store_true",
                    help="skip experimental rules (those interpreting "
                         "spec extensions like quantum/Schrödinger rebus)")
    ap.add_argument("--fix", action="store_true",
                    help="apply fixes for fixable rules and write to disk")
    ap.add_argument("--diff", action="store_true",
                    help="with --fix, print unified diff instead of writing "
                         "(implies --fix; exits 0 if there are no diffs)")
    ap.add_argument("--unsafe-fixes", action="store_true",
                    help="with --fix, include fixes that may alter semantics")
    ap.add_argument("--show-fixes", action="store_true",
                    help="with --fix, enumerate the fixes applied per file")
    args = ap.parse_args()

    # --diff implies --fix (matching ruff)
    if args.diff:
        args.fix = True

    if args.list_rules:
        print(f"{'CODE':<8} {'SEVERITY':<8} {'FLAGS':<10} NAME")
        rows = []
        for code, sev, name, experimental, _ in RULES:
            flags = []
            if experimental:
                flags.append("exp")
            if code in FIXERS:
                flags.append("ufix" if FIXERS[code][0] else "fix")
            rows.append((code, sev, name, ",".join(flags)))
        for code, sev, name in PARSER_LEVEL_FINDINGS:
            rows.append((code, sev, name, "parser"))
        for code, sev, name, flags in sorted(rows):
            print(f"{code:<8} {sev.value:<8} {flags:<10} {name}")
        return 0

    experimental_codes = {code for (code, _s, _n, exp, _f) in RULES if exp}

    if args.enable_only:
        active = {c.strip() for c in args.enable_only.split(",") if c.strip()}
    elif args.disable:
        disabled = {c.strip() for c in args.disable.split(",") if c.strip()}
        active = {code for (code, _s, _n, _e, _f) in RULES} - disabled
        # Parse-level findings (XD012/XD019/XD021/XD022) are emitted directly
        # by the parser, not via @rule, so they need to be added to `active`
        # explicitly or run_checks would filter them out.
        active |= {c for (c, _s, _n) in PARSER_LEVEL_FINDINGS} - disabled
    else:
        active = None

    if args.no_experimental:
        if active is None:
            # Same wrinkle as the --disable branch: parser-level findings
            # aren't in RULES, so build active from both sources or
            # run_checks would silently filter them out.
            active = {code for (code, _s, _n, _e, _f) in RULES} - experimental_codes
            active |= {c for (c, _s, _n) in PARSER_LEVEL_FINDINGS}
        else:
            active = active - experimental_codes

    if args.fix and args.base:
        ap.error("--fix is incompatible with --base "
                 "(which reads git blobs, not files on disk)")

    if args.base:
        source = contexts_from_git(args.base, args.head)
    elif args.paths:
        source = contexts_from_paths(args.paths)
    else:
        ap.error("give --base for git-diff mode, or explicit .xd paths")

    if args.fix:
        return _run_fix_mode(args, source, active)

    gate_rank = Severity(args.max_severity).rank
    checked = 0
    findings_total = 0
    gate_hit = 0

    for path, ctx in source:
        checked += 1
        for f in run_checks(ctx, active):
            if f.severity.rank < gate_rank:
                continue
            print(format_finding(path, f))
            findings_total += 1
            if f.severity.rank >= gate_rank:
                gate_hit += 1
        # Drop the slot cache for this ctx; otherwise large corpus runs
        # accumulate one entry per file forever.
        _SLOT_CACHE.pop(id(ctx), None)

    print(f"\nchecked {checked} file(s), {findings_total} finding(s) "
          f"at or above '{args.max_severity}'", file=sys.stderr)
    return 1 if gate_hit > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
