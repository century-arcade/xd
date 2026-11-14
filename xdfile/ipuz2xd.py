#!/usr/bin/env python3
# -*- coding: utf-8

"""Convert .ipuz crosswords (http://ipuz.org/, kind 'crossword') to .xd.

Reads the ipuz JSON directly (stdlib only), so the cell styles the
`crossword`/`ipuz` libraries drop are still available:

  * a null cell (an omitted square, e.g. letters printed outside the grid)
    becomes '_';
  * `"shapebg": "circle"` becomes a lowercase circled cell, as puz2xd does;
  * `"barred"` edges have no .xd representation yet.  They are kept on
    `xd.bars` ({(r, c): "T"|"L"|"TL"}) and reported with a warning, since
    without them the slots xd works out from the grid won't match the
    puzzle's own numbering.

Answers come from the grid, numbered the xd way, as in puz2xd.  A clue
whose number has no slot in that direction is still kept (with an empty
answer) and the conversion raises IncompletePuzzleParse, carrying the
partial xd, so the mismatch can't pass silently.
"""

import json
import re
import string

from .xdfile import (
    xdfile as XdFile, PuzzleParseError, IncompletePuzzleParse,
    REBUS_SEP, BLOCK_CHAR, OPEN_CHAR, UNKNOWN_CHAR,
)
from .puz2xd import decode, html_to_markup
from .utils import warn, clean_author_header, parse_pathname, parse_date_from_filename


REBUS_SHORTHANDS = "zyxwvutsrqponmlkjihgfedcba⚷⚳♇♆⛢♄♃♂♁♀☿♹♸♷♶♵♴♳⅘⅗⅖⅕♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠+&%$@?*0987654321"

_DIRECTIONS = {"across": "A", "down": "D"}


def _text(s, markup=True):
    if s is None:
        return ""
    return decode(html_to_markup(str(s), markup=markup)).strip()


def _cell_value(cell):
    """The solution value of an ipuz solution cell, or None for an omitted one."""
    if isinstance(cell, dict):
        cell = cell.get("value", cell.get("cell"))
    if cell is None:
        return None
    return str(cell)


def _cell_style(cell, styles):
    if not isinstance(cell, dict):
        return {}
    style = cell.get("style") or {}
    if isinstance(style, str):  # a named style from the puzzle's "styles"
        style = styles.get(style, {})
    return style


def _iter_clues(clue_list):
    """Yield (number, text) for each clue in one ipuz direction's list."""
    for item in clue_list:
        if isinstance(item, dict):
            number, text = item.get("number"), item.get("clue", "")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            number, text = item[0], item[1]
        elif isinstance(item, str):  # "12 Clue text"
            m = re.match(r'\s*(\d+)\.?\s+(.*)', item)
            number, text = (m.group(1), m.group(2)) if m else (None, item)
        else:
            raise PuzzleParseError("unrecognized ipuz clue: %r" % (item,))
        if isinstance(number, list):  # a clue over several numbers; xd keys on the first
            number = number[0]
        yield number, text


def parse_ipuz(contents, filename):
    if isinstance(contents, bytes):
        contents = contents.decode("utf-8-sig")
    try:
        ipz = json.loads(contents)
    except ValueError as e:
        raise PuzzleParseError("not ipuz JSON: %s" % e)

    kinds = ipz.get("kind") or []
    if not any("ipuz.org/crossword" in k for k in kinds):
        raise PuzzleParseError("not an ipuz crossword (kind %r)" % (kinds,))

    block = str(ipz.get("block", "#"))
    empty = str(ipz.get("empty", 0))
    styles = ipz.get("styles") or {}
    width = int(ipz["dimensions"]["width"])
    height = int(ipz["dimensions"]["height"])
    puzzle = ipz.get("puzzle") or [[None] * width] * height
    solution = ipz.get("solution")
    if not solution:
        raise PuzzleParseError("ipuz has no solution")

    xd = XdFile('', filename)
    xd.bars = {}

    author, editor = clean_author_header(_text(ipz.get("author"), markup=False))
    xd.set_header("Author", author)
    xd.set_header("Editor", _text(ipz.get("editor"), markup=False) or editor)
    xd.set_header("Copyright", _text(ipz.get("copyright"), markup=False))
    dt = parse_date_from_filename(parse_pathname(filename).base)
    if dt:
        xd.set_header("Date", dt)
    notes = [_text(ipz.get(k), markup=False) for k in ("intro", "notes")]
    xd.set_header("Notes", " ".join(n for n in notes if n))
    xd.set_header("Title", _text(ipz.get("title"), markup=False))

    grid_dict = dict(zip(string.ascii_uppercase, string.ascii_uppercase))
    shorthands = list(REBUS_SHORTHANDS)
    rebus = {}
    circles = False

    for r in range(height):
        rowstr = ""
        for c in range(width):
            pcell = puzzle[r][c] if r < len(puzzle) and c < len(puzzle[r]) else None
            scell = solution[r][c] if r < len(solution) and c < len(solution[r]) else None
            label = pcell.get("cell") if isinstance(pcell, dict) else pcell
            style = _cell_style(pcell, styles)
            value = _cell_value(scell)

            if style.get("barred"):
                xd.bars[(r, c)] = style["barred"].upper()

            if pcell is None and value is None:
                rowstr += OPEN_CHAR       # omitted square
                continue
            if value == block or (value is None and str(label) == block):
                rowstr += BLOCK_CHAR
                continue
            if value is None or value in (empty, ""):
                rowstr += UNKNOWN_CHAR
                continue

            ch = value.upper()
            if ch not in grid_dict:
                if len(ch) == 1 and ch in shorthands:
                    key = ch
                    shorthands.remove(ch)
                    warn("%s: unknown grid character '%s', assuming rebus of itself" % (filename, ch))
                else:
                    key = shorthands.pop()
                rebus[key] = ch
                grid_dict[ch] = key
            cellch = grid_dict[ch]
            if style.get("shapebg") == "circle":
                circles = True
                if cellch in string.ascii_uppercase:
                    cellch = cellch.lower()
                else:
                    warn("%s: circled rebus cell at r%d c%d; circle dropped" % (filename, r, c))
            rowstr += cellch
        xd.grid.append(rowstr)

    if rebus:
        xd.set_header("Rebus", REBUS_SEP.join("%s=%s" % kv for kv in sorted(rebus.items())))
    if circles:
        xd.set_header("Special", "circle")
    if xd.bars:
        warn("%s: barred grid (%d cells with bars); bars have no .xd form yet and are dropped"
             % (filename, len(xd.bars)))

    answers = {"%s%s" % (d[0], n): a for d, n, a in xd.iteranswers()}

    missing = []
    for dirkey, clue_list in (ipz.get("clues") or {}).items():
        dirname = dirkey.split(":")[0].strip().lower()
        if dirname not in _DIRECTIONS:
            warn("%s: clue group '%s' skipped" % (filename, dirkey))
            continue
        d = _DIRECTIONS[dirname]
        for number, text in _iter_clues(clue_list):
            try:
                num = int(number)
            except (TypeError, ValueError):
                num = number
            pos = "%s%s" % (d, num)
            if pos not in answers:
                missing.append(pos)
            xd.clues.append(((d, num), _text(text), answers.get(pos, "")))

    if missing:
        raise IncompletePuzzleParse(xd, "Clue numbers don't match grid: " + " ".join(missing))

    return xd


if __name__ == "__main__":
    import sys
    from .utils import find_files

    for fn, contents in find_files(*sys.argv[1:]):
        print(parse_ipuz(contents, fn).to_unicode())
