#!/usr/bin/env python3

# ailevel: 7
# This code (and its unit tests in tests/) was written by Claude Code Opus 4.6
# at the behest of a human developer over the course of several hours of iteration.
# Each rule was specified, reviewed, tested, and refined by a human.


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

Profiles (corpus policy on top of the format rules):
    --profile gxd    gxd's editorial conventions (gitlab.com/rabidrat/gxd
                     EDITORIAL.md, CONTRIBUTING.md): XD016 error -> info,
                     XD103 info -> warning, and the XD8xx rules. Rules for
                     new imports only (XD809, XD810) run on files the diff
                     adds in --base mode, and in path mode only with
                     --new-imports. See --list-rules --profile gxd.
    Without --profile, none of this applies.

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
import datetime
import difflib
import enum
import html
import os
import re
import shutil
import subprocess
import sys
import time
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
    # (line, text) for each non-blank line of the notes section.
    notes_lines: List[Tuple[int, str]] = field(default_factory=list)


@dataclass
class Ctx:
    filename: str
    text: str
    parsed: ParsedXd
    # --profile in effect (None = the plain catalog). See PROFILES.
    profile: Optional[str] = None
    # True when the file is a new import: added by the diff in --base mode,
    # or every file in path mode with --new-imports. Rules registered with
    # new_only=True run only on these.
    is_new: bool = False


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
    notes_numbered: List[Tuple[int, str]] = []
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
            notes_numbered.append((lineno, stripped))
        # else: section == "_unknown" — per spec, ignored entirely.

    return ParsedXd(
        text=text, lines=lines, section_mode=section_mode,
        headers=headers, grid=grid, clues=clues,
        notes_text="\n".join(notes_lines), parse_errors=parse_errors,
        unknown_sections=unknown_sections, notes_lines=notes_numbered,
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


# Profiles: corpus policy layered on top of the format rules, selected with
# --profile NAME. A profile can change the severity of catalog rules and
# owns rules of its own (registered with @rule(..., profile=NAME)), which
# run only under that profile. Without --profile none of this applies.
PROFILES: Dict[str, dict] = {
    "gxd": {
        "description": "gxd corpus policy (gitlab.com/rabidrat/gxd "
                       "EDITORIAL.md, CONTRIBUTING.md)",
        "severity": {
            # EDITORIAL.md "Incomplete puzzles": puzzles without answers
            # are welcome; unknown squares are '.'.
            "XD016": Severity.INFO,
            # EDITORIAL.md Headers: Editor: gets its own header.
            "XD103": Severity.WARNING,
        },
    },
}

# code -> profile name, for rules that only run under a profile.
RULE_PROFILE: Dict[str, str] = {}
# Rules that apply only to new imports (Ctx.is_new); see Ctx.
NEW_ONLY_RULES: set = set()
# code -> the policy document section a profile rule enforces, shown by
# --list-rules --profile NAME.
RULE_DOC: Dict[str, str] = {}


def rule(code: str, severity: Severity, name: str, experimental: bool = False,
         profile: Optional[str] = None, new_only: bool = False,
         doc: Optional[str] = None):
    """Register a check.

    experimental=True marks rules whose validation depends on conventions
    not formalized in the spec (currently: rules that interpret quantum
    or Schrödinger rebus syntax). Disabled by --no-experimental.

    profile=NAME registers a rule that runs only under --profile NAME.
    new_only=True limits it to new imports (Ctx.is_new). doc names the
    policy section a profile rule enforces.
    """
    def deco(fn: RuleFn) -> RuleFn:
        RULES.append((code, severity, name, experimental, fn))
        if profile is not None:
            assert profile in PROFILES, profile
            RULE_PROFILE[code] = profile
        if new_only:
            NEW_ONLY_RULES.add(code)
        if doc:
            RULE_DOC[code] = doc
        return fn
    return deco


def effective_severity(code: str, severity: Severity,
                       profile: Optional[str]) -> Severity:
    """A rule's severity once the profile's overrides are applied."""
    if profile is None:
        return severity
    return PROFILES[profile]["severity"].get(code, severity)


def rule_applies(code: str, ctx: "Ctx") -> bool:
    """Profile and new-import gating for one rule on one file."""
    owner = RULE_PROFILE.get(code)
    if owner is not None and owner != ctx.profile:
        return False
    if code in NEW_ONLY_RULES and not ctx.is_new:
        return False
    return True


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
    """Parse 'Rebus: 1=ONE 2=TWO 3=A/B' into {key: RebusExpansion}.

    Tolerates comma separators ('1=ONE,2=TWO') alongside whitespace so
    downstream rules don't choke on files that diverge from the spec.
    XD109 flags the comma form as a style violation."""
    out: Dict[str, RebusExpansion] = {}
    for part in re.split(r"[,\s]+", value.strip()):
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

    Splits the declared answer on ' / ' (one space, slash, one space)
    into candidate spellings and validates each against the slot. ALL
    candidates must validate. This accepts the spelled-out Schrödinger
    convention — e.g. 'TACK / RACK' for an across slot through a cell
    whose rebus alts are {T, R}, or 'CIGAR / PENIS' for an all-cells-
    Schrödinger answer — while rejecting inline-embedded forms like
    'T/RACK' that paste both readings mid-word (those fail because the
    bare '/' won't match the next grid cell). The space-flanked split
    leaves answers with literal '/' content (rebus value '1=/') intact.

    At each rebus cell, accepts any alt from either direction's
    expansion (union of across and down). Quantum-vs-Schrödinger
    distinction at the cell level is moot under this framing — the
    answer-line spelling chooses, not the rebus syntax.

    direction_idx is retained for callsite compatibility but no longer
    constrains which alts are acceptable.

    The xd-crossword-tools '|' word-split convention is stripped before
    splitting on ' / '."""
    declared = declared.replace("|", "")
    candidates = declared.split(" / ")
    for candidate in candidates:
        result = _walk_one_answer(candidate, cells, grid, rebus_map)
        if result is not None:
            return result
    return None


def _walk_one_answer(
    declared: str,
    cells: List[Tuple[int, int]],
    grid: List[GridRow],
    rebus_map: Dict[str, RebusExpansion],
) -> Optional[Tuple[str, str]]:
    """Match one candidate spelling against the slot's cells.

    At a rebus cell any alt from either direction's expansion is
    acceptable, tried longest first (1=A|AB, 1=KIT/KAT next to
    1=KITKAT) but with backtracking: two adjacent Schrödinger cells
    whose single-letter alts spell another cell's two-letter alt
    (1=E|A/EA 2=A|I/AI under D-E-A-L...) must not let the first cell
    swallow 'EA' and strand the second. When no path matches, the error
    reported is the first one the longest-first walk hit."""
    first_error: List[Tuple[str, str]] = []

    def fail(err: Tuple[str, str]) -> bool:
        if not first_error:
            first_error.append(err)
        return False

    def walk(ci: int, di: int) -> bool:
        if ci == len(cells):
            if di < len(declared):
                return fail(("XD006", f"answer has {len(declared) - di} extra "
                                      f"char(s) after position {di}"))
            return True
        r, c = cells[ci]
        ch = grid_get(grid, r, c)
        if ch in rebus_map:
            rebus = rebus_map[ch]
            alts = list(rebus.across)
            for a in rebus.down:
                if a not in alts:
                    alts.append(a)
            matched = False
            for alt in sorted(alts, key=len, reverse=True):
                if declared[di:di + len(alt)].upper() == alt:
                    matched = True
                    if walk(ci + 1, di + len(alt)):
                        return True
            if matched:
                return False
            if di >= len(declared):
                return fail(("XD006", "answer too short for slot"))
            expected = " or ".join(repr(a) for a in alts)
            fragment = declared[di:di + max((len(a) for a in alts), default=1)]
            return fail(("XD007", f"at position {di + 1}: expected {expected}, "
                                  f"found {fragment!r}"))
        if di >= len(declared):
            return fail(("XD006", "answer too short for slot"))
        if ch != WILDCARD_CHAR and declared[di].upper() != ch.upper():
            return fail(("XD007", f"at position {di + 1}: expected "
                                  f"{ch.upper()!r}, found {declared[di]!r}"))
        return walk(ci + 1, di + 1)

    if walk(0, 0):
        return None
    return first_error[0]


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


@rule("XD003", Severity.WARNING, "rebus-key-not-in-grid")
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
            yield finding("XD003", Severity.WARNING, rebus_header.line,
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


def _validations_for(ctx):
    """List of (clue, validation_result) for clues that map to a slot.
    Memoized per ctx so XD006 and XD007 share the per-clue validation
    work instead of each calling _validate_answer_against_slot
    independently. result is None on success or (code, message) on
    failure; the rules each filter on result[0]."""
    cache = getattr(ctx, "_validations", None)
    if cache is not None:
        return cache
    idx = _slot_index_or_none(ctx)
    if idx is None:
        ctx._validations = []
        return ctx._validations
    rebus_map = _rebus_for(ctx)
    out = []
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
        out.append((clue, result))
    ctx._validations = out
    return out


@rule("XD004", Severity.WARNING, "missing-slot-for-clue")
def _(ctx):
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    for clue in ctx.parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            yield finding("XD004", Severity.WARNING, clue.line,
                          f"clue {clue.pos} has no corresponding slot in grid")


@rule("XD005", Severity.WARNING, "clue-count-mismatch")
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
        yield finding("XD005", Severity.WARNING, line,
                      f"distinct clue positions {n_positions} "
                      f"!= grid slot count {n_slots}")


@rule("XD006", Severity.WARNING, "answer-length-mismatch", experimental=True)
def _(ctx):
    for clue, result in _validations_for(ctx):
        if result is not None and result[0] == "XD006":
            yield finding("XD006", Severity.WARNING, clue.line,
                          f"clue {clue.pos}: {result[1]} "
                          f"(declared={clue.answer!r})")


@rule("XD007", Severity.WARNING, "answer-grid-letter-mismatch", experimental=True)
def _(ctx):
    for clue, result in _validations_for(ctx):
        if result is not None and result[0] == "XD007":
            yield finding("XD007", Severity.WARNING, clue.line,
                          f"clue {clue.pos}: {result[1]} "
                          f"(declared={clue.answer!r})")


@rule("XD008", Severity.WARNING, "duplicate-clue-position", experimental=True)
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
            yield finding("XD008", Severity.WARNING, clue.line,
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
        for m in _A_GRAVE_FLATTENED_RE.finditer(line):
            yield finding("XD009", Severity.ERROR, i,
                          f"latin-1 misread of UTF-8 'à' at col "
                          f"{m.start() + 1}: 'Ã' + no-break space, flattened "
                          f"to 'Ã ' (should be 'à')")


# UTF-8 'à' (\xc3\xa0) misread as latin-1 is 'Ã' + NBSP, which
# _LATIN1_UTF8_RE catches; once the NBSP has been flattened to a space
# (XD208, or decode() before it handled 'à') only 'Ã ' is left
# ("Pied-Ã -terre"). Not after a capital, where 'Ã ' ends a real
# Portuguese word ("IRMÃ DULCE").
_A_GRAVE_FLATTENED_RE = re.compile(r"(?<![A-ZÀ-Þ])Ã ")


# U+FFFD is what a decoder writes for bytes it couldn't read, so a character
# was lost before or during conversion; 'ï¿½' is U+FFFD's UTF-8 bytes read
# as latin-1. Nothing says what the character was, so there's no fixer.
_REPLACEMENT_CHAR_RE = re.compile("�|ï¿½")


@rule("XD024", Severity.ERROR, "replacement-character")
def _(ctx):
    """U+FFFD (or its mojibake 'ï¿½') in the text: a character was lost,
    e.g. "Not to be @#$� with". Check the source or the published
    puzzle for what it was. Files that aren't valid UTF-8 get XD022
    instead, since their U+FFFDs come from the lint's own decode."""
    if any(f.code == "XD022" for f in ctx.parsed.parse_errors):
        return
    for i, line in enumerate(ctx.parsed.lines, 1):
        m = _REPLACEMENT_CHAR_RE.search(line)
        if m:
            yield finding("XD024", Severity.ERROR, i,
                          f"replacement character {m.group(0)!r} at col "
                          f"{m.start() + 1}: a character was lost")


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


@rule("XD703", Severity.WARNING, "deprecated-rebus-inline-embed")
def _(ctx):
    """Answer uses the deprecated inline-embed rebus form at a directional
    rebus cell — '<across>/<down>' pasted mid-word, e.g. 'J/POKER',
    'ALPH/FA', 'VIVIE/EINLEI/IEGH'. The canonical form spells out both
    readings: 'JOKER / POKER', 'ALPHA / ALFA'.

    The --fix expands inline-embed to spelled-out (information-preserving;
    no commitment to quantum vs. Schrödinger). For confirmed-quantum
    puzzles, a follow-up step collapses spelled-out to the directional
    half. Only fires on cells with one distinct alt per direction."""
    rebus_map = _rebus_for(ctx)
    if not rebus_map:
        return
    if not any(len(set(r.across) | set(r.down)) >= 2
               for r in rebus_map.values()):
        return  # no multi-alt rebus in this puzzle
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    for clue in ctx.parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            continue
        _direction, cells = idx[clue.pos]
        expanded = _expand_inline_embeds(
            clue.answer, cells, ctx.parsed.grid, rebus_map)
        if expanded is None:
            continue
        yield finding("XD703", Severity.WARNING, clue.line,
                      f"clue {clue.pos}: deprecated inline-embed rebus "
                      f"answer {clue.answer!r} (--fix expands to "
                      f"{expanded!r})")


@rule("XD704", Severity.WARNING, "rebus-quantum-collapse-available",
      experimental=True)
def _(ctx):
    """Sibling of XD703: same detection (inline-embed at a directional
    rebus cell), but the --fix collapses to the directional half (across
    keeps the left, down keeps the right) instead of expanding.

    Information-discarding — the non-directional half is dropped — so
    it should only be applied to puzzles classified as quantum. Marked
    experimental so it doesn't fire alongside XD703 by default; opt in
    with '--enable-only XD704 --fix' on a per-file basis once you've
    confirmed the puzzle isn't a Schrödinger."""
    rebus_map = _rebus_for(ctx)
    if not rebus_map:
        return
    if not any(len(set(r.across) | set(r.down)) >= 2
               for r in rebus_map.values()):
        return
    idx = _slot_index_or_none(ctx)
    if idx is None:
        return
    for clue in ctx.parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        if clue.pos not in idx:
            continue
        _direction, cells = idx[clue.pos]
        collapsed = _collapse_inline_embeds(
            clue.answer, cells, ctx.parsed.grid, rebus_map, clue.direction)
        if collapsed is None:
            continue
        yield finding("XD704", Severity.WARNING, clue.line,
                      f"clue {clue.pos}: rebus inline-embed "
                      f"{clue.answer!r} collapses to {collapsed!r} "
                      f"(quantum {clue.direction.lower()}-only reading)")


@rule("XD014", Severity.WARNING, "broken-ref")
def _(ctx):
    """Clue's ^Refs metadata names a position that doesn't exist."""
    positions = {c.pos for c in ctx.parsed.clues if c.pos}
    for clue in ctx.parsed.clues:
        refs = clue.metadata.get("refs")
        if not refs:
            continue
        for token in refs.split():
            if token not in positions:
                yield finding("XD014", Severity.WARNING, clue.line,
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


@rule("XD023", Severity.WARNING, "unclosed-parenthetical")
def _(ctx):
    """Clue body has an opening '(' that begins a parenthetical but no
    matching ')'. Filtered to avoid common false positives:
      - '(' must be at start of body or preceded by a space (skips smileys
        like ':-(' where the paren is glued to the prior char)
      - '(' must NOT be the last non-space char of the body (skips trailing
        '(' which is more likely a smiley remnant than a real parenthetical)
      - The character after '(' must not be ',' or '.' (skips clues whose
        answer cues the literal '(' character, e.g. '(, for example' ~ PAREN)
    """
    for clue in ctx.parsed.clues:
        body = clue.body.rstrip()
        if not body:
            continue
        opens = 0
        for i, ch in enumerate(body):
            if ch != "(":
                continue
            if i > 0 and body[i-1] != " ":
                continue
            if i == len(body) - 1:
                continue
            if body[i+1] in ",.":
                continue
            opens += 1
        closes = body.count(")")
        if opens > closes:
            yield finding("XD023", Severity.WARNING, clue.line,
                          f"clue {clue.pos} has an unclosed '(' parenthetical")


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


# --profile gxd also catches 'Smith; Ed. By Jones' and 'Smith, Ed. Jones'.
# Same pattern as xdfile.utils._AUTHOR_EDITOR_RE, which the converters use.
_AUTHOR_EDITOR_RE_GXD = re.compile(
    r"/\s*Ed(?:itor|\.)?\b|edited by|[;,]\s*Ed\.", re.IGNORECASE)


def _author_editor_re(profile: Optional[str]):
    return _AUTHOR_EDITOR_RE_GXD if profile == "gxd" else _AUTHOR_EDITOR_RE


@rule("XD103", Severity.INFO, "editor-folded-into-author")
def _(ctx):
    """Author header value carries editor info ('Smith / Ed. Jones',
    'Smith; edited by Jones'). Split-out via --fix is available but
    optional — the spec does not require a separate Editor header.
    Under --profile gxd it is a warning (gxd EDITORIAL.md, Headers:
    Editor: has a header of its own [established]) and also matches
    'Smith; Ed. Jones'."""
    pattern = _author_editor_re(ctx.profile)
    for h in ctx.parsed.headers:
        if h.key.lower() != "author":
            continue
        if pattern.search(h.value):
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


@rule("XD109", Severity.WARNING, "non-canonical-rebus-separator")
def _(ctx):
    """The spec separates Rebus entries with single spaces:
        Rebus: 1=ONE 2=TWO 3=THREE
    Files using commas ('1=ONE,2=TWO') parse correctly under the
    permissive parser, but the comma form is a corpus-wide style
    violation — flag it so it can be migrated."""
    for h in ctx.parsed.headers:
        if h.key.lower() != "rebus":
            continue
        if "," in h.value:
            yield finding("XD109", Severity.WARNING, h.line,
                          "Rebus header uses comma separators; spec uses spaces")


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


# Spec markup forms: {/italic/}, {*bold*}, {_underscore_}, {-strike-}, and
# from the v4 draft {~subscript~}, {^superscript^}, {=small caps=},
# {@link | href: ...@}, {!image | src: ...!}, {\literal\} and {#color#}.
# A span opens with '{' and a type character and closes with the same type
# character and '}'; spans may nest, and {\\} (an empty literal) is a line
# break.
_CLUE_MARKUP_RE = re.compile(r"\{([/*_\-~^=@!\\#])(.*?)\1\}")


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


# Cryptic crossword detection (adapted from scripts/91-find-cryptics in
# alexdej/wip). Two near-orthogonal signals: (1) lattice grids have many
# 1-cell across/down slots, very rare in American-style puzzles; (2) cryptic
# clues conventionally end with an answer-length annotation like "(5)" or
# "(3,4)". Both signals together → high confidence. One alone → suspect.
# Cryptic length annotations are word-length tallies (1-2 digits, e.g.
# "(5)" or "(3,4)"). Years like "(2010)" at the end of a clue are NOT
# cryptic hints; capping at 2 digits filters those out.
_CRYPTIC_LEN_RE = re.compile(r"\(\d{1,2}(?:[,\s]+\d{1,2})*\)\s*$")
_CRYPTIC_GRID_THRESHOLD = 5
_CRYPTIC_CLUE_THRESHOLD = 5


def _count_singleton_slots(grid):
    """Return (across_singletons, down_singletons) where a singleton is a
    non-block cell with blocks (or edges) on both sides along that axis."""
    h = len(grid)
    if h == 0:
        return 0, 0
    w = max(len(r.cells) for r in grid)

    def cell(y, x):
        if y < 0 or y >= h or x < 0 or x >= w:
            return "#"
        row = grid[y].cells
        return row[x] if x < len(row) else "#"

    across = 0
    for y in range(h):
        for x in range(w):
            c = cell(y, x)
            if c == "#":
                continue
            if cell(y, x - 1) == "#" and cell(y, x + 1) == "#":
                across += 1
    down = 0
    for y in range(h):
        for x in range(w):
            c = cell(y, x)
            if c == "#":
                continue
            if cell(y - 1, x) == "#" and cell(y + 1, x) == "#":
                down += 1
    return across, down


@rule("XD309", Severity.INFO, "likely-cryptic")
def _(ctx):
    """File looks like a cryptic crossword (lattice grid + length-annotated
    clues). Emits one finding per file with the confidence and signal counts."""
    grid = ctx.parsed.grid
    if not grid:
        return
    across, down = _count_singleton_slots(grid)
    grid_signal = across + down
    clue_signal = sum(
        1 for c in ctx.parsed.clues if _CRYPTIC_LEN_RE.search(c.body)
    )
    if (grid_signal >= _CRYPTIC_GRID_THRESHOLD
            and clue_signal >= _CRYPTIC_CLUE_THRESHOLD):
        confidence = "high"
    elif (grid_signal >= _CRYPTIC_GRID_THRESHOLD
          or clue_signal >= _CRYPTIC_CLUE_THRESHOLD):
        confidence = "review"
    else:
        return
    yield finding(
        "XD309", Severity.INFO, 1,
        f"likely cryptic ({confidence}): grid_singletons={grid_signal} "
        f"(A={across},D={down}), clue_length_hints={clue_signal}"
    )


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


# Typography characters that puz2xd's decode() flattens to ASCII on import
# (see doc/character-encoding.md §9 step 7 and step 2). Files imported
# pre-flatten or via non-puz2xd pipelines retain these. Em dash (U+2014)
# is *not* in this set: corpus convention keeps it as Unicode (FITB marker
# in NYT/Wapost/Eltana, per doc/character-encoding.md §11).
_TYPOGRAPHY_FLATTEN = {
    "‘": "'",    # left single quote
    "’": "'",    # right single quote
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "…": "...",  # horizontal ellipsis
    " ": " ",    # no-break space
}
_TYPOGRAPHY_RE = re.compile("[" + "".join(_TYPOGRAPHY_FLATTEN) + "]")


@rule("XD208", Severity.WARNING, "non-ascii-typography")
def _(ctx):
    """Non-ASCII typography that puz2xd's decode() would have flattened on
    import: curly quotes, ellipsis, NBSP. Auto-fixable via --fix; saves a
    full reimport for files that escaped the flatten step."""
    for i, line in enumerate(ctx.parsed.lines, 1):
        for m in _TYPOGRAPHY_RE.finditer(line):
            ch = m.group(0)
            cp = ord(ch)
            yield finding("XD208", Severity.WARNING, i,
                          f"non-ascii typography U+{cp:04X} {ch!r} at "
                          f"col {m.start() + 1} (flatten to "
                          f"{_TYPOGRAPHY_FLATTEN[ch]!r})")


# Interior run of 2+ ASCII spaces. Anchored to non-space on both sides so
# leading indentation and trailing whitespace are out of scope (XD201
# handles trailing). Grid rows are skipped at the call site — a run of
# spaces inside a grid is XD002's domain, not a typography issue.
_MULTI_SPACE_RE = re.compile(r"(?<=\S) {2,}(?=\S)")


@rule("XD209", Severity.WARNING, "multiple-internal-spaces")
def _(ctx):
    """Run of 2+ ASCII spaces between non-space characters. puz2xd's
    decode() collapses these on import (re.sub(r'\\s+', ' ', s)); files
    that escaped the collapse retain them. Skips grid rows."""
    grid_lines = {row.line for row in ctx.parsed.grid}
    for i, line in enumerate(ctx.parsed.lines, 1):
        if i in grid_lines:
            continue
        m = _MULTI_SPACE_RE.search(line)
        if m:
            yield finding("XD209", Severity.WARNING, i,
                          f"run of {len(m.group(0))} spaces at "
                          f"col {m.start() + 1} (collapse to single space)")


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
    "XD208",  # curly quotes / ellipsis / NBSP -> ASCII (after XD011 because
              # &hellip; etc. unescape to a flagged char first)
    "XD110",  # de-indent '## Section' headers
    "XD203",  # de-indent grid rows
    "XD204",  # tabs -> spaces
    "XD201",  # trim trailing whitespace
    "XD209",  # collapse interior runs of 2+ spaces (after XD201 so trailing
              # runs are already gone; after XD204/XD208 so tabs and NBSPs
              # have already become regular spaces)
    "XD103",  # split editor out of Author header
    "XD802",  # move 'Edited by X' out of Copyright into Editor (gxd)
    "XD801",  # drop 'By ' from Author (gxd; after XD103, which already
              # drops it from an Author it splits)
    "XD107",  # drop duplicate header lines (after XD103: lets XD103 pick the
              # editor-bearing Author even if it isn't the first one, then
              # cleans up the duplicate it leaves behind)
    "XD109",  # rewrite comma separators in the Rebus header to spaces
    "XD202",  # reorder canonical headers (picks up the new Editor)
    "XD102",  # collapse 2+ blank lines in clues to 1
    "XD013",  # synthesize ^Refs from cross-refs in clue bodies
    "XD703",  # expand deprecated inline-embed rebus answers ('IE/EI'
              # mid-word) to the canonical spelled-out form ('IE / EI');
              # depends on a sane Rebus header so XD109 must run first
    "XD704",  # alternative collapse to directional alt; experimental and
              # opt-in via --enable-only XD704. Skips inputs containing
              # ' / ', so when both XD703 and XD704 are active (default
              # --fix run) XD703 expands first and XD704 becomes a no-op.
    "XD023",  # append ')' to clues with one unclosed parenthetical; unsafe
              # because the close-paren placement is heuristic (end-of-body).
]


# Fixers whose behavior depends on --profile take it as a keyword,
# fn(text, profile=None); the rest are called as fn(text).
PROFILE_AWARE_FIXERS: set = set()


def fixer(code: str, unsafe: bool = False, profile_aware: bool = False):
    def deco(fn: FixerFn) -> FixerFn:
        FIXERS[code] = (unsafe, fn)
        if profile_aware:
            PROFILE_AWARE_FIXERS.add(code)
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
    + cont-byte) re-decoded through latin-1 -> UTF-8 round-trip.

    Special case: 'Ã\\x82' (puz bytes \\xc3\\x82) is a known stray-mojibake
    artifact in the corpus -- not real text. Stripped rather than re-decoded,
    which would produce a literal 'Â' (U+00C2) sitting in the middle of clue
    text. Mirrors the explicit strip in xdfile/puz2xd.py decode().

    'Ã ' (an 'à' whose no-break space was flattened) becomes 'à': the space
    was the NBSP, but a following space may have been collapsed into it,
    so it's kept except before a hyphen ("Pied-Ã -terre" -> "Pied-à-terre",
    "Ã la" -> "à la").
    """
    count = 0
    def repl(m):
        nonlocal count
        s = m.group(0)
        if s == '\xc3\x82':
            count += 1
            return ''
        try:
            replacement = s.encode('latin-1').decode('utf-8')
        except UnicodeDecodeError:
            return s
        count += 1
        return replacement
    text = _LATIN1_UTF8_RE.sub(repl, text)

    def repl_a_grave(m):
        nonlocal count
        count += 1
        return 'à' if text[m.end():m.end() + 1] == '-' else 'à '
    return _A_GRAVE_FLATTENED_RE.sub(repl_a_grave, text), count


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


@fixer("XD208")
def _(text):
    """Flatten curly quotes / ellipsis / NBSP to ASCII. Mirrors puz2xd's
    decode() steps 2 and 7."""
    count = sum(1 for ch in text if ch in _TYPOGRAPHY_FLATTEN)
    if not count:
        return text, 0
    new = text.translate({ord(k): v for k, v in _TYPOGRAPHY_FLATTEN.items()})
    return new, count


@fixer("XD209")
def _(text):
    """Collapse interior runs of 2+ spaces to a single space, on every line
    except grid rows. Mirrors the trailing whitespace-collapse in decode()."""
    parsed = parse(text)
    grid_lines = {row.line for row in parsed.grid}
    count = 0
    out = []
    for i, line in enumerate(text.splitlines(keepends=True), 1):
        if i in grid_lines:
            out.append(line)
            continue
        new, n = _MULTI_SPACE_RE.subn(" ", line)
        if n:
            count += n
        out.append(new)
    return "".join(out), count


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


def _detect_inline_embed_pair(declared, di, alts):
    """At position `di` in declared, look for an inline-embed
    '<X>/<Y>' where X, Y are distinct alts of the current rebus.
    Returns (left_alt, right_alt, total_consumed) on hit, else None.

    Tries longer pairs first so a 'LW/L|W'-style compound rebus —
    where the alts are {LW, L, W} — picks the right pair instead
    of greedily eating a shorter prefix first."""
    sorted_alts = sorted(alts, key=len, reverse=True)
    for x in sorted_alts:
        for y in sorted_alts:
            if x == y:
                continue
            full = x + "/" + y
            if declared[di:di + len(full)].upper() == full:
                return (x, y, len(full))
    return None


def _expand_inline_embeds(declared, cells, grid, rebus_map):
    """Expand the deprecated inline-embed rebus answer form (e.g.
    'J/POKER', 'ALPH/FA', 'VIVIE/EINLEI/IEGH', 'RACHEL/WEISZ') to the
    canonical spelled-out form ('JOKER / POKER', 'ALPHA / ALFA', etc.)
    — two full spellings of the slot with one inline-embed half at
    every rebus cell going to the left output and the other to the
    right.

    Information-preserving: produces both spellings instead of
    committing to a directional collapse. For Schrödinger puzzles this
    is the canonical form; for quantum puzzles a follow-up pass
    collapses spelled-out → directional once classified.

    Returns the rewritten string, or None if the answer can't be
    cleanly walked or contains no inline-embeds. Skips inputs already
    in spelled-out form (any ' / ' present).

    Inline-embed detection accepts any '<X>/<Y>' pair drawn from a
    rebus cell's alts (across ∪ down), so straight quantum (1=A/B),
    bare Schrödinger (1=A|B), and compound forms (1=LW/L|W where the
    inline-embed halves are the down Schrödinger pair) all match."""
    if " / " in declared:
        return None

    left_out = []
    right_out = []
    di = 0
    found_inline = False

    for (r, c) in cells:
        ch = grid_get(grid, r, c)
        if ch in rebus_map:
            rebus = rebus_map[ch]
            alts = list(rebus.across)
            for a in rebus.down:
                if a not in alts:
                    alts.append(a)
            inline = _detect_inline_embed_pair(declared, di, alts)
            if inline is not None:
                left, right, consumed = inline
                left_out.append(left)
                right_out.append(right)
                di += consumed
                found_inline = True
                continue
            # No inline-embed at this cell — consume a single alt.
            matched = False
            for alt in sorted(alts, key=len, reverse=True):
                if declared[di:di + len(alt)].upper() == alt:
                    chunk = declared[di:di + len(alt)]
                    left_out.append(chunk)
                    right_out.append(chunk)
                    di += len(alt)
                    matched = True
                    break
            if not matched:
                return None
        elif ch == WILDCARD_CHAR:
            if di >= len(declared):
                return None
            left_out.append(declared[di])
            right_out.append(declared[di])
            di += 1
        else:
            if di >= len(declared):
                return None
            if declared[di].upper() != ch.upper():
                return None
            left_out.append(declared[di])
            right_out.append(declared[di])
            di += 1

    if di < len(declared):
        return None
    if not found_inline:
        return None
    return "".join(left_out) + " / " + "".join(right_out)


def _collapse_inline_embeds(declared, cells, grid, rebus_map, direction):
    """Collapse inline-embed rebus answers to one half of the inline
    pair: across keeps the left half of '<X>/<Y>', down keeps the right.
    Returns rewritten string, or None if the answer can't be cleanly
    walked or has no inline-embed.

    Skips spelled-out form (' / ' present) — apply this fix to original
    inline-embed input only, since spelled-out form has already lost the
    inline-embed structural cue.

    Inline-embed detection mirrors XD703's expand: any '<X>/<Y>' pair
    drawn from a rebus cell's alts (across ∪ down). Note this means the
    'left' for compound rebuses (1=LW/L|W) is the matched alt order
    found by the detector, not necessarily across vs. down."""
    if " / " in declared:
        return None
    direction_idx = 0 if direction == "A" else 1
    out = []
    di = 0
    found_inline = False
    for (r, c) in cells:
        ch = grid_get(grid, r, c)
        if ch in rebus_map:
            rebus = rebus_map[ch]
            alts = list(rebus.across)
            for a in rebus.down:
                if a not in alts:
                    alts.append(a)
            inline = _detect_inline_embed_pair(declared, di, alts)
            if inline is not None:
                left, right, consumed = inline
                out.append(left if direction_idx == 0 else right)
                di += consumed
                found_inline = True
                continue
            matched = False
            for alt in sorted(alts, key=len, reverse=True):
                if declared[di:di + len(alt)].upper() == alt:
                    out.append(declared[di:di + len(alt)])
                    di += len(alt)
                    matched = True
                    break
            if not matched:
                return None
        elif ch == WILDCARD_CHAR:
            if di >= len(declared):
                return None
            out.append(declared[di])
            di += 1
        else:
            if di >= len(declared):
                return None
            if declared[di].upper() != ch.upper():
                return None
            out.append(declared[di])
            di += 1
    if di < len(declared):
        return None
    if not found_inline:
        return None
    return "".join(out)


@fixer("XD703")
def _(text):
    """Expand the deprecated inline-embed rebus answer form to the
    canonical spelled-out Schrödinger form. 'J/POKER' becomes
    'JOKER / POKER'; 'VIVIE/EINLEI/IEGH' becomes
    'VIVIENLEIGH / VIVEINLIEGH'.

    Information-preserving (the down half is kept rather than
    discarded), reversible, and direction-agnostic. For puzzles that
    are actually quantum (where only one half is the real answer), a
    follow-up classification + collapse step picks the directional
    half. The expansion is a safe first move regardless of which case
    the puzzle turns out to be.

    Conservative: only acts at cells with one distinct alt per
    direction — multi-alt Schrödingers (rebus '1=A|B') and unrelated
    XD007 letter-mismatches are left alone."""
    parsed = parse(text)
    if not parsed.grid or not parsed.clues:
        return text, 0
    rebus_map = parse_rebus_header(get_header(parsed, "Rebus") or "")
    if not rebus_map:
        return text, 0

    slots = enumerate_slots(parsed.grid)
    idx = {(d, n): cells for (d, n, _r, _c, cells) in slots}

    rewrites = {}
    for clue in parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        cells = idx.get((clue.direction, clue.number))
        if cells is None:
            continue
        expanded = _expand_inline_embeds(
            clue.answer, cells, parsed.grid, rebus_map)
        if expanded is not None and expanded != clue.answer:
            rewrites[clue.line] = expanded

    if not rewrites:
        return text, 0

    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines, 1):
        if i in rewrites:
            stripped = line.rstrip("\r\n")
            ending = line[len(stripped):]
            tilde = stripped.rfind(" ~ ")
            if tilde < 0:
                out.append(line)
                continue
            out.append(stripped[:tilde + 3] + rewrites[i] + ending)
        else:
            out.append(line)
    return "".join(out), len(rewrites)


@fixer("XD704")
def _(text):
    """Collapse inline-embed rebus answers to the directional half:
    'J/POKER' becomes 'JOKER' for across clues, 'POKER' for down.
    Information-discarding sibling of the XD703 expand fixer — apply
    only to puzzles confirmed to be quantum (across/down readings
    differ; not Schrödinger). Conservative: only acts at cells with
    one distinct alt per direction."""
    parsed = parse(text)
    if not parsed.grid or not parsed.clues:
        return text, 0
    rebus_map = parse_rebus_header(get_header(parsed, "Rebus") or "")
    if not rebus_map:
        return text, 0

    slots = enumerate_slots(parsed.grid)
    idx = {(d, n): cells for (d, n, _r, _c, cells) in slots}

    rewrites = {}
    for clue in parsed.clues:
        if clue.direction not in ("A", "D"):
            continue
        cells = idx.get((clue.direction, clue.number))
        if cells is None:
            continue
        collapsed = _collapse_inline_embeds(
            clue.answer, cells, parsed.grid, rebus_map, clue.direction)
        if collapsed is not None and collapsed != clue.answer:
            rewrites[clue.line] = collapsed

    if not rewrites:
        return text, 0

    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines, 1):
        if i in rewrites:
            stripped = line.rstrip("\r\n")
            ending = line[len(stripped):]
            tilde = stripped.rfind(" ~ ")
            if tilde < 0:
                out.append(line)
                continue
            out.append(stripped[:tilde + 3] + rewrites[i] + ending)
        else:
            out.append(line)
    return "".join(out), len(rewrites)


@fixer("XD109")
def _(text):
    """Replace comma separators in the Rebus header with single spaces.
    Header keys can't contain commas, so a line-wide substitution on the
    Rebus line is safe."""
    parsed = parse(text)
    rebus_lines = {h.line for h in parsed.headers
                   if h.key.lower() == "rebus" and "," in h.value}
    if not rebus_lines:
        return text, 0
    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines, 1):
        if i in rebus_lines:
            stripped = line.rstrip("\r\n")
            ending = line[len(stripped):]
            out.append(re.sub(r"\s*,\s*", " ", stripped) + ending)
        else:
            out.append(line)
    return "".join(out), len(rebus_lines)


# Port of clean_author() from scripts/21-clean-metadata.py. Splits an Author
# value that looks like "Smith / Ed. Jones" or "Smith; edited by Jones" into
# (author, editor). Empty-author cases (e.g. "Edited by Smith") get returned
# as ("", "Smith"); the fixer below treats those as out-of-scope.
# Kept in lockstep with xdfile.utils.split_author_editor(), which the
# converters use for new imports; tests/test_xdlint.py checks that the two
# agree. (xdlint.py stays standalone, so it can't import xdfile.)
_CLEAN_AUTHOR_RE = re.compile(
    r"(?i)(?:(?:By )*(.+)(?:[;/,-]|and) *)?"
    r"(?:edited|Editor|(?<!\w)Ed[.])(?: By)*(.*)"
)
# A trailing '.' that ends an initial or Jr./Sr. is part of the name
# ('S.N., edited by Stanley Newman' keeps 'S.N.').
_NAME_FINAL_PERIOD_RE = re.compile(r"(?:\b[A-Z]|\bJr|\bSr)\.$")
_BY_PREFIX_RE = re.compile(r"^(?:by\s+)+", re.IGNORECASE)


def _strip_by_prefix(s: str) -> str:
    """'By Mike Shenk' -> 'Mike Shenk'; unchanged if nothing would remain."""
    rest = _BY_PREFIX_RE.sub("", s)
    return rest if rest.strip() else s


def _trim_name(s: str) -> str:
    s = s.strip().rstrip(",").strip()
    if s.endswith(".") and not _NAME_FINAL_PERIOD_RE.search(s):
        s = s[:-1].rstrip()
    return s


def _clean_author(author: str, editor: str) -> Tuple[str, str]:
    if author:
        m = _CLEAN_AUTHOR_RE.search(author)
        if m:
            author, editor = m.groups()
        if author:
            while author.lower().startswith("by "):
                author = author[3:]
            author = _trim_name(author)
        else:
            author = ""
        if " / " in author and not editor:
            author, editor = author.rsplit(" / ", 1)
    if editor:
        editor = editor.strip()
        while editor.lower().startswith("by "):
            editor = editor[3:].strip()
        editor = _trim_name(editor)
    return (author or "").strip(), (editor or "").strip()


@fixer("XD103", profile_aware=True)
def _(text, profile=None):
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
    pattern = _author_editor_re(profile)
    author_h = next((h for h in parsed.headers
                     if h.key.lower() == "author"
                     and pattern.search(h.value)), None)
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


@fixer("XD023", unsafe=True)
def _(text):
    """Append ')' to clue body when there's exactly one unclosed '('
    parenthetical (per XD023's filters) and no orphan '}'/']' that would
    hint at a wrong-bracket-type defect. Marked unsafe because the right
    place for the ')' is heuristic — most defects in the corpus are
    truncated trailing parentheticals where end-of-body is correct, but a
    midline-dropped close would be silently misplaced."""
    parsed = parse(text)
    if not parsed.clues:
        return text, 0
    target_lines = set()
    for clue in parsed.clues:
        body = clue.body.rstrip()
        if not body:
            continue
        opens = 0
        for i, ch in enumerate(body):
            if ch != "(":
                continue
            if i > 0 and body[i-1] != " ":
                continue
            if i == len(body) - 1:
                continue
            if body[i+1] in ",.":
                continue
            opens += 1
        closes = body.count(")")
        if opens != closes + 1:
            continue
        # Skip wrong-bracket-type cases (e.g. '(through}'); those need a
        # human edit, not an appended ')'.
        if body.count("{") != body.count("}"):
            continue
        if body.count("[") != body.count("]"):
            continue
        target_lines.add(clue.line)
    if not target_lines:
        return text, 0
    out = []
    count = 0
    for i, line in enumerate(text.splitlines(keepends=True), 1):
        if i in target_lines:
            idx = line.rfind(" ~ ")
            if idx > 0:
                out.append(line[:idx] + ")" + line[idx:])
                count += 1
            else:
                out.append(line)
        else:
            out.append(line)
    return "".join(out), count


# ---------------------------------------------------------------------------
# XD8xx - gxd corpus policy (--profile gxd)
# ---------------------------------------------------------------------------
# These rules enforce gxd's editorial conventions, not the .xd format, so
# they run only under --profile gxd. Each names the section of gxd's
# EDITORIAL.md or CONTRIBUTING.md (gitlab.com/rabidrat/gxd) it enforces.
# Severity follows the convention's status there: [established] and
# [practice] are warnings, [proposed] is info. Rules for [proposed]
# conventions that apply to new imports only are new_only (see Ctx.is_new).

def _line_ending(s: str) -> str:
    if s.endswith("\r\n"):
        return "\r\n"
    if s.endswith("\n"):
        return "\n"
    return ""


def _notes_texts(parsed: ParsedXd) -> List[Tuple[int, str]]:
    """(line, text) for the notes: Section 4 plus any Notes: header."""
    out = [(h.line, h.value) for h in parsed.headers
           if h.key.lower() == "notes" and h.value.strip()]
    return out + list(parsed.notes_lines)


@rule("XD801", Severity.WARNING, "author-by-prefix", profile="gxd",
      doc="EDITORIAL.md Headers, Author: no 'By ' prefix [established]")
def _(ctx):
    """Author: is the constructor's name in a normalized form, with no
    'By ' prefix (gxd EDITORIAL.md, Headers, Author:, [established])."""
    for h in ctx.parsed.headers:
        if h.key.lower() == "author" and _strip_by_prefix(h.value) != h.value:
            yield finding("XD801", Severity.WARNING, h.line,
                          f"Author {h.value!r} starts with 'By '; gxd's "
                          f"Author: is the name only (EDITORIAL.md, Headers)")


@fixer("XD801")
def _(text):
    """Drop a leading 'By ' from Author: values."""
    parsed = parse(text)
    lines = text.splitlines(keepends=True)
    fixes = 0
    for h in parsed.headers:
        if h.key.lower() != "author":
            continue
        new = _strip_by_prefix(h.value)
        if new != h.value:
            i = h.line - 1
            lines[i] = f"{h.key}: {new}{_line_ending(lines[i])}"
            fixes += 1
    return "".join(lines), fixes


# 'Edited by X' (or 'Ed. by X', 'Editor: X') inside Copyright:. A bare
# 'Ed. X' is not matched: in a rights line 'ed.' can also mean edition.
_COPYRIGHT_EDITOR_RE = re.compile(
    r"\bedited\s+by\b|(?<!\w)ed\.\s*by\b|\beditor\s*:", re.IGNORECASE)
_NAME_WORD_RE = re.compile(
    r"^(?:[A-Z][\w.'-]*|[A-Z]\.|and|&|de|del|der|van|von|la|le|du|di)$")


def _copyright_editor_split(value: str) -> Optional[Tuple[str, str]]:
    """('Copyright 2026 X; Edited by Jane Doe') -> ('Copyright 2026 X',
    'Jane Doe') when the editor credit can be cut out unambiguously:
    one credit, followed by a plain name and then the end of the value or
    a separator. None otherwise."""
    matches = list(_COPYRIGHT_EDITOR_RE.finditer(value))
    if len(matches) != 1:
        return None
    m = matches[0]
    rest = value[m.end():]
    nm = re.match(r"\s*([^;,|/()]+?)\s*(?=$|[;,|/()])", rest)
    if not nm:
        return None
    name = _trim_name(nm.group(1))
    words = name.split()
    if not 1 <= len(words) <= 5 or not all(_NAME_WORD_RE.match(w) for w in words):
        return None
    before = value[:m.start()].rstrip()
    before = re.sub(r"[\s;,|/-]+$", "", before)
    after = rest[nm.end():].lstrip()
    if before and after:
        after = re.sub(r"^[;,|/]\s*", "", after)
        remainder = f"{before}; {after}" if after else before
    else:
        remainder = (before or re.sub(r"^[;,|/]\s*", "", after)).strip()
    return remainder, name


@rule("XD802", Severity.WARNING, "editor-in-copyright", profile="gxd",
      doc="EDITORIAL.md Headers, Editor: and Copyright: [established]")
def _(ctx):
    """Copyright: holds only the rights or syndication line; the editor
    has an Editor: header of its own (gxd EDITORIAL.md, Headers, Editor:
    and Copyright:, [established]). The Author: case is XD103."""
    for h in ctx.parsed.headers:
        if h.key.lower() == "copyright" and _COPYRIGHT_EDITOR_RE.search(h.value):
            yield finding("XD802", Severity.WARNING, h.line,
                          "Copyright contains an editor credit; gxd puts the "
                          "editor in Editor: (EDITORIAL.md, Headers)")


@fixer("XD802")
def _(text):
    """Move the editor credit out of Copyright: into Editor:, when it can
    be cut out unambiguously and no different Editor: is already set."""
    parsed = parse(text)
    cr = next((h for h in parsed.headers if h.key.lower() == "copyright"
               and _COPYRIGHT_EDITOR_RE.search(h.value)), None)
    if cr is None:
        return text, 0
    split = _copyright_editor_split(cr.value)
    if split is None:
        return text, 0
    remainder, name = split
    editor_h = next((h for h in parsed.headers
                     if h.key.lower() == "editor"), None)
    if editor_h is not None and editor_h.value and editor_h.value != name:
        return text, 0
    lines = text.splitlines(keepends=True)
    nl = _detect_nl(text)
    ci = cr.line - 1
    if remainder:
        lines[ci] = f"{cr.key}: {remainder}{_line_ending(lines[ci])}"
    else:
        lines[ci] = None
    if editor_h is None:
        author_h = next((h for h in parsed.headers
                         if h.key.lower() == "author"), None)
        at = author_h.line if author_h else cr.line - 1
        lines.insert(at, f"Editor: {name}{nl}")
    elif not editor_h.value:
        ei = editor_h.line - 1
        lines[ei] = f"{editor_h.key}: {name}{_line_ending(lines[ei])}"
    return "".join(x for x in lines if x is not None), 1


# '<pubid>-<number>[a-z]' (cc-0948, nediger-219_5, dab-279a). Same shape as
# the numbered-xdid pattern in xdfile/catalog.py shelf_path_from_xdid().
_NUMBERED_STEM_RE = re.compile(r"^([a-z]+)-(\d[A-Za-z0-9_]*?)([a-z]?)$")
# Pubids whose number is an id, not a place in a numbered series, so
# Number: doesn't apply. nytpack-<n>: the number is the NYT's puzzle id.
_NOT_SERIES_NUMBER_PUBIDS = {"nytpack"}


def _norm_number(s: str) -> str:
    """Number: value or file-name number, compared the way xdids are built
    (xdfile.number_slug): drop 'No.'/'#', non-alphanumerics become '_',
    case and leading zeros ignored."""
    s = re.sub(r"(?i)^(?:no\.?|#)\s*", "", s.strip())
    s = re.sub(r"[^A-Za-z0-9]", "_", s).lower()
    return s.lstrip("0") or "0"


@rule("XD803", Severity.WARNING, "numbered-xdid-number", profile="gxd",
      doc="CONTRIBUTING.md Numbered series; EDITORIAL.md Headers, "
          "Number: [practice]")
def _(ctx):
    """A file named for a numbered series, <pubid>-<number>[a-z].xd, needs
    a Number: header that matches the number in its name (gxd
    CONTRIBUTING.md, xdids, Numbered series; EDITORIAL.md, Headers,
    Number:, [practice]). Provisional (unshelved) names are skipped, and
    so are pubids whose number isn't a series number (nytpack)."""
    base = os.path.basename(ctx.filename.replace("\\", "/"))
    if "unshelved" in base or not base.endswith(".xd"):
        return
    m = _NUMBERED_STEM_RE.match(base[:-3])
    if not m or m.group(1) in _NOT_SERIES_NUMBER_PUBIDS:
        return
    num, suffix = m.group(2), m.group(3)
    number_h = next((h for h in ctx.parsed.headers
                     if h.key.lower() == "number"), None)
    if number_h is None or not number_h.value.strip():
        yield finding("XD803", Severity.WARNING, number_h.line if number_h else 0,
                      f"file name is numbered ({num}) but there is no "
                      f"Number: header (CONTRIBUTING.md, Numbered series)")
        return
    got = _norm_number(number_h.value)
    if got not in (_norm_number(num), _norm_number(num + suffix)):
        yield finding("XD803", Severity.WARNING, number_h.line,
                      f"Number: {number_h.value!r} doesn't match the number "
                      f"in the file name ({num})")


def _phrase_re(phrase: str):
    words = phrase.split()
    return re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, words)) + r"(?!\w)",
                      re.IGNORECASE)


@rule("XD804", Severity.WARNING, "meta-answer-in-notes", profile="gxd",
      doc="EDITORIAL.md Headers, Meta: [practice]")
def _(ctx):
    """'Meta: <prompt> ~ <answer>': the answer never goes in the notes,
    because solving software shows the notes before the solve (gxd
    EDITORIAL.md, Headers, Meta:, [practice]). Whole-word, case-insensitive
    match; answers under 4 letters are skipped as too noisy, and so are
    answers that the prompt itself contains."""
    notes = _notes_texts(ctx.parsed)
    if not notes:
        return
    for h in ctx.parsed.headers:
        if h.key.lower() != "meta":
            continue
        prompt, sep, answer = h.value.rpartition("~")
        answer = answer.strip()
        if not sep or len(re.sub(r"\W", "", answer)) < 4:
            continue
        pat = _phrase_re(answer)
        if pat.search(prompt):
            continue
        for line, text in notes:
            if pat.search(text):
                yield finding("XD804", Severity.WARNING, line,
                              f"notes give the Meta: answer {answer!r} "
                              f"(EDITORIAL.md, Headers, Meta:)")
                break


# The markup kinds EDITORIAL.md lists: italic, bold, underline, strike,
# superscript, subscript.
_PLAIN_TEXT_MARKUP_RE = re.compile(r"\{([/*_\-^~])(.+?)\1\}")


@rule("XD805", Severity.WARNING, "markup-outside-clues", profile="gxd",
      doc="EDITORIAL.md Characters and typography, Markup only in clues "
          "[established]")
def _(ctx):
    """Markup ({/italic/}, {*bold*}, {_underline_}, {-strike-}, {^sup^},
    {~sub~}) belongs only in clues; headers and notes are plain text (gxd
    EDITORIAL.md, Characters and typography, [established])."""
    for h in ctx.parsed.headers:
        m = _PLAIN_TEXT_MARKUP_RE.search(h.value)
        if m:
            yield finding("XD805", Severity.WARNING, h.line,
                          f"markup {m.group(0)!r} in header {h.key}: "
                          f"headers are plain text (EDITORIAL.md)")
    for line, text in ctx.parsed.notes_lines:
        m = _PLAIN_TEXT_MARKUP_RE.search(text)
        if m:
            yield finding("XD805", Severity.WARNING, line,
                          f"markup {m.group(0)!r} in the notes: notes are "
                          f"plain text (EDITORIAL.md)")


_SIC_RE = re.compile(r"\[sic\]", re.IGNORECASE)


@rule("XD806", Severity.INFO, "annotation-in-clue", profile="gxd",
      doc="EDITORIAL.md Clues and grid: no '[sic]' in clues [practice]; "
          "for review")
def _(ctx):
    """Clues are the publisher's text, with no '[sic]' or other
    annotations of ours (gxd EDITORIAL.md, Clues and grid, [practice]).
    For review, not fixing: a text match can't tell our '[sic]' from the
    publisher's own (a clue about the word, a quotation), and in the
    corpus today every hit is the publisher's. Hence info, not warning."""
    for clue in ctx.parsed.clues:
        if _SIC_RE.search(clue.body):
            yield finding("XD806", Severity.INFO, clue.line,
                          f"clue {clue.pos} contains '[sic]'; check it is the "
                          f"publisher's text, not an annotation "
                          f"(EDITORIAL.md, Clues and grid)")


_MISSING_CLUE_PLACEHOLDER = "[XXX]"


@rule("XD807", Severity.WARNING, "missing-clue-not-noted", profile="gxd",
      doc="EDITORIAL.md Incomplete puzzles: a missing clue is [XXX], "
          "and the notes say what is missing [practice]")
def _(ctx):
    """A missing clue is filed as gxd's '[XXX]' placeholder, and the notes
    say what is missing (gxd EDITORIAL.md, Incomplete puzzles,
    [practice]). Fires when the file has placeholders but no notes at
    all; whether the notes cover every placeholder is left to review."""
    placeholders = [c for c in ctx.parsed.clues
                    if c.body.strip() == _MISSING_CLUE_PLACEHOLDER]
    if not placeholders or _notes_texts(ctx.parsed):
        return
    first = placeholders[0]
    more = f" (and {len(placeholders) - 1} more)" if len(placeholders) > 1 else ""
    yield finding("XD807", Severity.WARNING, first.line,
                  f"clue {first.pos} is the {_MISSING_CLUE_PLACEHOLDER} "
                  f"placeholder{more} but there are no notes saying what is "
                  f"missing (EDITORIAL.md, Incomplete puzzles)")


_PROVENANCE_RE = re.compile(
    r"(?i:\blitzed\s+by\b|\bdownloaded\s+from\b|\bconverted\s+(?:from|by)\b"
    r"|\bscanned\s+by\b)|\bOCR(?:'d|ed)?\b")


@rule("XD808", Severity.INFO, "provenance-in-notes", profile="gxd",
      doc="EDITORIAL.md Notes, What does not go in the notes [practice]; "
          "heuristic")
def _(ctx):
    """Where the puzzle came from and how it was made (download details,
    OCR caveats, 'Litzed by ...') goes in receipts and the source
    archive's NOTES.md, not the notes (gxd EDITORIAL.md, Notes, What does
    not go in the notes, [practice]). A phrase match, so info."""
    for line, text in _notes_texts(ctx.parsed):
        m = _PROVENANCE_RE.search(text)
        if m:
            yield finding("XD808", Severity.INFO, line,
                          f"notes mention {m.group(0)!r}; provenance goes in "
                          f"receipts, not the notes (EDITORIAL.md, Notes)")


@rule("XD809", Severity.INFO, "author-ampersand", profile="gxd",
      new_only=True,
      doc="EDITORIAL.md Headers, Author: join with 'and' [proposed]; "
          "new imports only")
def _(ctx):
    """Two constructors are joined with 'and', not '&' (gxd EDITORIAL.md,
    Headers, Author:, [proposed] for new imports; existing files are not
    changed, so this runs only on new imports)."""
    for h in ctx.parsed.headers:
        if h.key.lower() == "author" and "&" in h.value:
            yield finding("XD809", Severity.INFO, h.line,
                          "Author joins names with '&'; gxd uses 'and' for "
                          "new imports (EDITORIAL.md, Headers)")


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]
_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                  "Saturday", "Sunday"]
_DATE_EXPR = (
    r"(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+)?"
    r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})"
)
# A title that is only a date, in any form ('October 06, 2026', 'Tue, Oct 6,
# 2026', '10/6/2026'). A title with a label before the date ('LA Times, Mon,
# Jan 6, 2020', 'The Crossword: Tuesday, October 6, 2026') is not matched:
# EDITORIAL.md leaves outlet-name-and-date titles as an open question, and a
# label can't be told from a puzzle's name ('Palme d'Or, Sun. May 1, 2016').
_DATE_TITLE_RE = re.compile(r"^" + _DATE_EXPR + r"$", re.IGNORECASE)


_CANONICAL_DATE_TITLE_RE = re.compile(
    r"^(?:" + "|".join(_WEEKDAY_NAMES) + r"), (?:" + "|".join(_MONTH_NAMES)
    + r") [1-9]\d?, \d{4}$")


def _canonical_date_title(iso: str) -> Optional[str]:
    try:
        dt = datetime.date.fromisoformat(iso.strip())
    except ValueError:
        return None
    return (f"{_WEEKDAY_NAMES[dt.weekday()]}, {_MONTH_NAMES[dt.month - 1]} "
            f"{dt.day}, {dt.year}")


@rule("XD810", Severity.INFO, "date-title-form", profile="gxd",
      new_only=True,
      doc="EDITORIAL.md Headers, Title: date titles [proposed]; "
          "new imports only")
def _(ctx):
    """When a puzzle's only title is its date, the title is the date in the
    form 'Tuesday, October 6, 2026': full weekday and month, no zero
    padding, no outlet name (gxd EDITORIAL.md, Headers, Title:,
    [proposed]; existing files are not changed, so this runs only on new
    imports). Checks titles that are a bare date; titles with an outlet
    label before the date are an open question there and are not
    flagged."""
    title_h = next((h for h in ctx.parsed.headers
                    if h.key.lower() == "title"), None)
    if title_h is None or not _DATE_TITLE_RE.match(title_h.value.strip()):
        return
    title = title_h.value.strip()
    want = _canonical_date_title(get_header(ctx.parsed, "date") or "")
    if title == want or (want is None and _CANONICAL_DATE_TITLE_RE.match(title)):
        return
    form = (f"{want!r} (from Date:)" if want
            else "like 'Tuesday, October 6, 2026'")
    yield finding("XD810", Severity.INFO, title_h.line,
                  f"date title {title_h.value!r}: gxd's form is {form}, "
                  f"with no zero padding (EDITORIAL.md, Headers)")


def apply_fixes(text: str, codes: Optional[set], unsafe_ok: bool,
                profile: Optional[str] = None) -> Tuple[str, Dict[str, int]]:
    """Apply fixers in canonical order. Each fixer is idempotent and
    reparses internally if needed, so a single pass is sufficient.
    Fixers for a profile's own rules run only under that profile."""
    counts: Dict[str, int] = {}
    for code in FIX_ORDER:
        if codes is not None and code not in codes:
            continue
        if code not in FIXERS:
            continue
        owner = RULE_PROFILE.get(code)
        if owner is not None and owner != profile:
            continue
        unsafe, fn = FIXERS[code]
        if unsafe and not unsafe_ok:
            continue
        if code in PROFILE_AWARE_FIXERS:
            new_text, n = fn(text, profile=profile)
        else:
            new_text, n = fn(text)
        if new_text != text:
            counts[code] = counts.get(code, 0) + n
            text = new_text
    return text, counts


# ---------------------------------------------------------------------------
# Driver: source of (path, ctx) pairs
# ---------------------------------------------------------------------------

def iter_xd_paths(roots):
    """Yield .xd file paths under each root (file or directory).

    Paths are emitted with forward slashes regardless of platform so the
    finding output is bash/git-bash-friendly on Windows (where os.walk
    otherwise produces 'gxd/nytimes/2022\\nyt...' with mixed separators
    that downstream shells can't resolve).

    A nonexistent root prints to stderr and is skipped — silently
    walking nothing for a typo'd path turned into a 'checked 0 file(s)'
    surprise too easily."""
    for root in roots:
        if not os.path.exists(root):
            print(f"{root}: no such file or directory", file=sys.stderr)
            continue
        if os.path.isfile(root):
            if root.endswith(".xd"):
                yield root.replace("\\", "/")
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".xd"):
                    yield os.path.join(dirpath, fn).replace("\\", "/")


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


def contexts_from_paths(paths, profile=None, new_imports=False):
    """Returns (total_count, generator-of-(path, Ctx)). The list is
    materialized so the caller can show progress. Memory cost is just
    the path strings; file contents are still read lazily.

    new_imports=True marks every file as a new import (Ctx.is_new); path
    mode can't tell otherwise."""
    file_paths = list(iter_xd_paths(paths))

    def gen():
        for path in file_paths:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                print(f"{path}\tIO\terror reading: {e}", file=sys.stderr)
                continue
            text, decode_findings = _decode_with_findings(data)
            parsed = parse(text)
            parsed.parse_errors[:0] = decode_findings
            yield path, Ctx(filename=path, text=text, parsed=parsed,
                            profile=profile, is_new=new_imports)

    return len(file_paths), gen()


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


def contexts_from_git(base, head, profile=None):
    """Lint files added or modified between two refs. Files the diff adds
    are new imports (Ctx.is_new).

    Returns (total_count, generator-of-(path, Ctx))."""
    out = _git("diff", "--name-status", "--diff-filter=AM", f"{base}..{head}")
    paths = []
    added = set()
    for row in out.splitlines():
        status, _, p = row.partition("\t")
        if not p.endswith(".xd"):
            continue
        paths.append(p)
        if status.startswith("A"):
            added.add(p)
    blobs = _batch_show(head, paths)

    def gen():
        for path in paths:
            content = blobs.get(path)
            if content is None:
                continue
            text, decode_findings = _decode_with_findings(content)
            parsed = parse(text)
            parsed.parse_errors[:0] = decode_findings
            yield path, Ctx(filename=path, text=text, parsed=parsed,
                            profile=profile, is_new=path in added)

    return len(paths), gen()


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------

def _format_duration(seconds: float) -> str:
    """Compact h:mm:ss / m:ss formatter for elapsed/eta values."""
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


class _Progress:
    """Single-line, in-place progress reporter for long corpus runs.

    Throttles redraws to ~10/sec so a fast inner loop doesn't spend more
    time on terminal I/O than on actual work. Always renders the final
    tick. When disabled, every method is a no-op."""

    def __init__(self, total: int, enabled: bool, stream=None):
        self.total = total
        self.enabled = enabled
        # Resolve sys.stderr lazily so redirect_stderr() (in tests) and any
        # late-bound replacement of sys.stderr are honored.
        self.stream = stream if stream is not None else sys.stderr
        self.start = time.monotonic()
        self.last_draw = 0.0
        self.n = 0
        self.drew = False

    def tick(self, current: str = "") -> None:
        self.n += 1
        if not self.enabled:
            return
        now = time.monotonic()
        if (now - self.last_draw) < 0.1 and self.n != self.total:
            return
        self.last_draw = now
        self._draw(current)

    def _draw(self, current: str) -> None:
        elapsed = time.monotonic() - self.start
        if self.n > 0 and elapsed > 0 and self.total > 0:
            eta = (self.total - self.n) * (elapsed / self.n)
        else:
            eta = 0.0
        pct = 100.0 * self.n / self.total if self.total else 0.0
        width = len(str(self.total))
        prefix = (f"[{self.n:>{width}}/{self.total}] {pct:5.1f}% "
                  f"elapsed {_format_duration(elapsed)} "
                  f"eta {_format_duration(eta)} ")
        cols = shutil.get_terminal_size((100, 20)).columns
        room = max(0, cols - len(prefix) - 1)
        if len(current) > room and room > 3:
            current = "..." + current[-(room - 3):]
        elif len(current) > room:
            current = ""
        self.stream.write("\r\033[K" + prefix + current)
        self.stream.flush()
        self.drew = True

    def done(self) -> None:
        if self.enabled and self.drew:
            self.stream.write("\r\033[K")
            self.stream.flush()


def _progress_enabled(arg: str, stream=None) -> bool:
    if arg == "always":
        return True
    if arg == "never":
        return False
    if stream is None:
        stream = sys.stderr
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _run_checks_raw(ctx: Ctx, active_codes):
    for f in ctx.parsed.parse_errors:
        if active_codes is None or f.code in active_codes:
            yield f
    for code, severity, _name, _experimental, fn in RULES:
        if active_codes is not None and code not in active_codes:
            continue
        if not rule_applies(code, ctx):
            continue
        try:
            yield from fn(ctx)
        except Exception as e:
            yield finding(code, severity, 0,
                          f"rule raised {type(e).__name__}: {e}")


def run_checks(ctx: Ctx, active_codes):
    """Yield findings from the parser plus all active rules, with the
    severities of ctx.profile (if any) applied."""
    overrides = PROFILES[ctx.profile]["severity"] if ctx.profile else {}
    for f in _run_checks_raw(ctx, active_codes):
        sev = overrides.get(f.code)
        if sev is not None and sev != f.severity:
            f = Finding(code=f.code, severity=sev, line=f.line,
                        message=f.message)
        yield f


def format_finding(path, f: Finding) -> str:
    loc = f"{path}:{f.line}" if f.line else path
    return f"{loc}\t{f.severity.value}\t{f.code}\t{f.message}"


def _run_fix_mode(args, total, source, active_codes):
    """Apply fixers per file, then re-lint and report what's left.
    With --diff, print diffs to stdout and skip writing."""
    fix_codes = {c for c in FIXERS
                 if RULE_PROFILE.get(c) in (None, args.profile)}
    if active_codes is not None:
        fix_codes &= active_codes

    files_seen = 0
    files_changed = 0
    total_fixes = 0
    findings_total = 0
    gate_hit = 0
    gate_rank = Severity(args.max_severity).rank
    progress = _Progress(total, _progress_enabled(args.progress))

    for path, ctx in source:
        files_seen += 1
        progress.tick(path)

        # If the file has decode errors, skip — the in-memory text already
        # has U+FFFD replacements and writing it back would lose bytes.
        if any(f.code == "XD022" for f in ctx.parsed.parse_errors):
            print(f"{path}\tinfo\tskip\tnot fixing: file has non-UTF-8 bytes",
                  file=sys.stderr)
            _SLOT_CACHE.pop(id(ctx), None)
            continue

        new_text, counts = apply_fixes(ctx.text, fix_codes, args.unsafe_fixes,
                                       profile=args.profile)
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
                fixed_ctx = Ctx(filename=path, text=new_text, parsed=fixed_parsed,
                                profile=ctx.profile, is_new=ctx.is_new)
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

    progress.done()

    if args.diff:
        if not args.quiet:
            print(f"\n{files_changed} of {files_seen} file(s) would be modified",
                  file=sys.stderr)
        return 1 if files_changed > 0 else 0

    if not args.quiet:
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
    ap.add_argument("--profile", choices=sorted(PROFILES),
                    help="apply a corpus policy on top of the format rules: "
                         "adjusts some severities and enables the "
                         "profile's own rules (gxd: XD8xx; see "
                         "--list-rules --profile gxd)")
    ap.add_argument("--new-imports", action="store_true",
                    help="path mode: treat every file as a new import, so "
                         "rules for new imports only (XD809, XD810) run too. "
                         "Without it they are skipped in path mode. In diff "
                         "mode (--base) they run on files the diff adds, "
                         "not on modified ones")
    ap.add_argument("--fix", action="store_true",
                    help="apply fixes for fixable rules and write to disk")
    ap.add_argument("--diff", action="store_true",
                    help="with --fix, print unified diff instead of writing "
                         "(implies --fix; exits 0 if there are no diffs)")
    ap.add_argument("--unsafe-fixes", action="store_true",
                    help="with --fix, include fixes that may alter semantics")
    ap.add_argument("--show-fixes", action="store_true",
                    help="with --fix, enumerate the fixes applied per file")
    ap.add_argument("--progress", choices=["auto", "always", "never"],
                    default="auto",
                    help="progress reporting on stderr (default: auto = on "
                         "when stderr is a tty)")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="suppress trailing summary line and live progress; "
                         "findings and warnings still print")
    args = ap.parse_args()

    # --diff implies --fix (matching ruff)
    if args.diff:
        args.fix = True

    # --quiet forces progress off too; the summary line is its primary target,
    # but a live progress bar would also be unwanted in quiet mode.
    if args.quiet:
        args.progress = "never"

    if args.list_rules:
        # With --profile: effective severities, plus the profile's rules
        # (flagged with the profile name; 'new' = new imports only) and the
        # policy section each enforces. Without it, the plain catalog.
        prof = args.profile
        overrides = PROFILES[prof]["severity"] if prof else {}
        print(f"{'CODE':<8} {'SEVERITY':<8} {'FLAGS':<10} NAME")
        rows = []
        for code, sev, name, experimental, _ in RULES:
            owner = RULE_PROFILE.get(code)
            if owner is not None and owner != prof:
                continue
            flags = []
            if experimental:
                flags.append("exp")
            if code in FIXERS:
                flags.append("ufix" if FIXERS[code][0] else "fix")
            if owner is not None or code in overrides:
                flags.append(prof)
            if code in NEW_ONLY_RULES:
                flags.append("new")
            if code in RULE_DOC:
                name = f"{name}  ({RULE_DOC[code]})"
            rows.append((code, effective_severity(code, sev, prof), name,
                         ",".join(flags)))
        for code, sev, name in PARSER_LEVEL_FINDINGS:
            flags = "parser" + (f",{prof}" if code in overrides else "")
            rows.append((code, effective_severity(code, sev, prof), name, flags))
        for code, sev, name, flags in sorted(rows):
            print(f"{code:<8} {sev.value:<8} {flags:<10} {name}")
        if prof:
            print(f"\nprofile {prof}: {PROFILES[prof]['description']}")
        return 0

    if args.new_imports and args.base:
        ap.error("--new-imports is for path mode; with --base, files the "
                 "diff adds are the new imports")

    experimental_codes = {code for (code, _s, _n, exp, _f) in RULES if exp}

    # All codes the runtime knows about: rule codes, parser-level finding
    # codes, and fixer-only codes. Used to validate --enable-only/--disable
    # so a typo'd code fails loudly instead of silently selecting nothing.
    known_codes = (
        {code for (code, _s, _n, _e, _f) in RULES}
        | {c for (c, _s, _n) in PARSER_LEVEL_FINDINGS}
        | set(FIXERS.keys())
    )

    if args.enable_only:
        active = {c.strip() for c in args.enable_only.split(",") if c.strip()}
        unknown = active - known_codes
        if unknown:
            ap.error(f"unknown rule code(s) in --enable-only: "
                     f"{','.join(sorted(unknown))}")
    elif args.disable:
        disabled = {c.strip() for c in args.disable.split(",") if c.strip()}
        unknown = disabled - known_codes
        if unknown:
            ap.error(f"unknown rule code(s) in --disable: "
                     f"{','.join(sorted(unknown))}")
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

    # A profile's own rules do nothing without that profile; say so rather
    # than silently selecting nothing.
    if args.enable_only:
        foreign = sorted(c for c in active
                         if RULE_PROFILE.get(c) not in (None, args.profile))
        if foreign:
            ap.error(f"rule(s) {','.join(foreign)} run only under "
                     f"--profile {RULE_PROFILE[foreign[0]]}")

    if args.fix and args.base:
        ap.error("--fix is incompatible with --base "
                 "(which reads git blobs, not files on disk)")

    # When --fix is set with --enable-only, catch silent-no-op cases:
    #   - selected rule has no fixer registered
    #   - selected rule has an unsafe fixer but --unsafe-fixes is off
    # Warn for each affected code; error if NO selected rule will produce
    # any fix (the entire --fix run would be a no-op).
    if args.fix and args.enable_only:
        selected = {c.strip() for c in args.enable_only.split(",") if c.strip()}
        no_fixer = sorted(selected - set(FIXERS.keys()))
        unsafe_skipped = sorted(
            c for c in selected
            if c in FIXERS and FIXERS[c][0] and not args.unsafe_fixes
        )
        runnable = {
            c for c in selected
            if c in FIXERS and (not FIXERS[c][0] or args.unsafe_fixes)
        }
        if not runnable:
            parts = []
            if no_fixer:
                parts.append(f"no fixer for {','.join(no_fixer)}")
            if unsafe_skipped:
                parts.append(f"unsafe fixer(s) {','.join(unsafe_skipped)} "
                             f"need --unsafe-fixes")
            ap.error(f"--fix with --enable-only={args.enable_only}: "
                     f"nothing to fix ({'; '.join(parts)})")
        if no_fixer:
            print(f"warning: --fix has no effect for selected rule(s) "
                  f"{','.join(no_fixer)} (no fixer registered)",
                  file=sys.stderr)
        if unsafe_skipped:
            print(f"warning: --fix skipping unsafe fixer(s) "
                  f"{','.join(unsafe_skipped)} (pass --unsafe-fixes to apply)",
                  file=sys.stderr)

    if args.base:
        total, source = contexts_from_git(args.base, args.head,
                                          profile=args.profile)
    elif args.paths:
        total, source = contexts_from_paths(args.paths, profile=args.profile,
                                            new_imports=args.new_imports)
    else:
        ap.error("give --base for git-diff mode, or explicit .xd paths")

    if args.fix:
        return _run_fix_mode(args, total, source, active)

    gate_rank = Severity(args.max_severity).rank
    checked = 0
    findings_total = 0
    gate_hit = 0
    progress = _Progress(total, _progress_enabled(args.progress))

    for path, ctx in source:
        checked += 1
        progress.tick(path)
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

    progress.done()

    if not args.quiet:
        print(f"\nchecked {checked} file(s), {findings_total} finding(s) "
              f"at or above '{args.max_severity}'", file=sys.stderr)
    return 1 if gate_hit > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
