# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Crossword Compiler XML (.xml, also the .jpz payload) -> .xd

Handles the <crossword-compiler> and <crossword-compiler-applet> roots, with
or without their namespaces.  Keeps rebus cells (Rebus:), circles and shading
(Special:, lowercase cells), void cells ('_'), inline markup in clues
(flattened to plain text) and the puzzle description (section 4 notes).
"""

import html
import re
import string
from lxml import etree

import xdfile
from xdfile.utils import warn


HEADER_RENAMES = {
    'Creator': 'Author',
}

# metadata children that become headers (all others are ignored or go to notes)
HEADER_TAGS = ('title', 'creator', 'copyright', 'editor', 'publisher')

# puz2xd's decode() flattens these on import; keep converted text consistent
TYPOGRAPHY_FLATTEN = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    " ": " ",
}

# Same key order as puz2xd: digits first, then symbols; lowercase letters are
# reserved for cells that are both rebus and Special.
REBUS_KEYS = list("123456789" "0*?@$%&+" "♠♥♦♣⚀⚁⚂⚃⚄⚅♟♞♝♜♛♚⅕⅖⅗⅘♳♴♵♶♷♸♹☿♀♁♂♃♄⛢♆♇⚳⚷")

CIRCLE = 'circle'
SHADED = 'shaded'


def _ln(el):
    """local name of an element, namespace stripped"""
    return etree.QName(el).localname


def _children(el, name):
    if el is None:
        return []
    return [c for c in el if isinstance(c.tag, str) and _ln(c) == name]


def _find(el, name):
    """first descendant with this local name, or None"""
    for c in el.iter():
        if isinstance(c.tag, str) and _ln(c) == name:
            return c
    return None


MOJIBAKE_RE = re.compile('[ÂÃ]')
TAG_RE = re.compile(r'</?[a-zA-Z][^<>]*>')


def _flatten(s):
    """plain text: entities decoded, stray tags dropped, UTF-8 read as
    latin-1 undone, curly quotes and friends flattened"""
    s = html.unescape(s)
    s = TAG_RE.sub('', s)
    if MOJIBAKE_RE.search(s):
        try:
            s = s.encode('latin-1').decode('utf-8')
        except UnicodeError:
            pass
    for k, v in TYPOGRAPHY_FLATTEN.items():
        s = s.replace(k, v)
    return s


def _text(el):
    """all text inside an element, inline markup dropped, whitespace collapsed"""
    return " ".join(_flatten("".join(el.itertext())).split())


def _paragraphs(el):
    """text with inline markup dropped, blank-line paragraph breaks kept"""
    s = _flatten("".join(el.itertext()))
    paras = [" ".join(p.split()) for p in re.split(r'\n\s*\n', s)]
    return "\n\n".join(p for p in paras if p)


def _is_dark(color):
    """background colors that stand for a block (black or near-black)"""
    m = re.fullmatch(r'#([0-9a-fA-F]{6})', color or '')
    if not m:
        return False
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return max(r, g, b) < 0x40


# data is bytes()
def parse_ccxml(data, filename):
    try:
        root = etree.fromstring(data)
    except Exception as e:
        warn("%s: not XML (%s)" % (filename, e))
        return None

    rect = _find(root, 'rectangular-puzzle')
    if rect is None:
        return None
    grid = _find(rect, 'grid')
    if grid is None:
        return None

    rows = int(grid.attrib['height'])
    cols = int(grid.attrib['width'])

    xd = xdfile.xdfile('', filename)

    # headers and notes
    md = _find(rect, 'metadata')
    if md is not None:
        for el in md:
            if not isinstance(el.tag, str):
                continue
            tag = _ln(el)
            if tag in HEADER_TAGS:
                text = _text(el)
                if not text:
                    continue
                key = HEADER_RENAMES.get(tag.title(), tag.title())
                if key == 'Author':
                    # "Jane Doe (edited by John Roe)" -> Author / Editor
                    m = re.fullmatch(r'(.*?)\s*\(edited by ([^)]+)\)', text, re.I)
                    if m:
                        text = m.group(1)
                        xd.set_header('Editor', m.group(2).strip())
                xd.set_header(key, text)
            elif tag == 'description':
                notes = _paragraphs(el)
                if notes:
                    xd.notes = notes + xdfile.EOL

    # cells
    solutions = {}  # (row, col) -> full solution string
    circles = set()
    shaded = set()
    black_letters = {}  # (row, col) -> letter printed in a black square
    bars = 0
    undefined = rows * cols
    puzzle = [[xdfile.OPEN_CHAR] * cols for _ in range(rows)]

    for cell in _children(grid, 'cell'):
        x = int(cell.attrib['x']) - 1
        y = int(cell.attrib['y']) - 1
        if not (0 <= x < cols and 0 <= y < rows):
            warn("%s: cell (%d,%d) outside %dx%d grid" % (filename, x + 1, y + 1, cols, rows))
            continue
        undefined -= 1
        ctype = cell.attrib.get('type', '')
        sol = cell.attrib.get('solution', '')
        bg = cell.attrib.get('background-color', '')
        if cell.attrib.get('top-bar') == 'true' or cell.attrib.get('left-bar') == 'true':
            bars += 1

        if ctype == 'block':
            puzzle[y][x] = xdfile.BLOCK_CHAR
        elif ctype == 'void':
            puzzle[y][x] = xdfile.OPEN_CHAR
        elif _is_dark(bg):
            # A cell drawn black is a block in all but name.  Some gimmick
            # puzzles print letters in black squares; .xd has no way to show
            # that, so the letters go in the notes (below).
            puzzle[y][x] = xdfile.BLOCK_CHAR
            if sol.strip():
                black_letters[(y, x)] = sol.strip()
        elif not sol.strip():
            puzzle[y][x] = xdfile.OPEN_CHAR
            warn("%s: cell (%d,%d) has no solution; left open" % (filename, x + 1, y + 1))
        else:
            sol = sol.strip()
            solutions[(y, x)] = sol
            if cell.attrib.get('background-shape') == 'circle':
                circles.add((y, x))
            if bg and bg.upper() != '#FFFFFF':
                shaded.add((y, x))

    if undefined:
        warn("%s: %d of %d cells undefined; left open" % (filename, undefined, rows * cols))
    if bars:
        warn("%s: %d cells with bars; bars are not representable in .xd" % (filename, bars))

    # Special: the spec allows one kind of marked cell per puzzle
    special = set()
    if circles:
        special = circles
        xd.set_header('Special', CIRCLE)
        if shaded - circles:
            warn("%s: %d shaded cells dropped (puzzle also has circles)" % (
                filename, len(shaded - circles)))
    elif shaded:
        special = shaded
        xd.set_header('Special', SHADED)

    # rebus keys: one per distinct multi-character solution, digits first;
    # a rebus cell that is also Special gets a lowercase letter key
    rebus = {}        # key -> solution
    plain_keys = {}   # solution -> key, for unmarked cells
    letter_keys = {}  # solution -> key, for Special cells
    free_keys = list(REBUS_KEYS)
    # a lowercase letter already standing for a Special single letter can't
    # also be a rebus key
    marked_letters = {sol.lower() for rc, sol in solutions.items()
                      if rc in special and len(sol) == 1 and sol.isalpha()}
    free_letters = [ch for ch in string.ascii_lowercase if ch not in marked_letters]

    for (y, x), sol in sorted(solutions.items()):
        if len(sol) == 1 and sol.isascii() and sol.isalpha():
            ch = sol.upper()
            puzzle[y][x] = ch.lower() if (y, x) in special else ch
            continue
        if (y, x) in special:
            if sol not in letter_keys:
                if not free_letters:
                    warn("%s: out of lowercase rebus keys" % filename)
                    break
                letter_keys[sol] = free_letters.pop(0)
                rebus[letter_keys[sol]] = sol
            puzzle[y][x] = letter_keys[sol]
        else:
            if sol not in plain_keys:
                if not free_keys:
                    warn("%s: out of rebus keys" % filename)
                    break
                plain_keys[sol] = free_keys.pop(0)
                rebus[plain_keys[sol]] = sol
            puzzle[y][x] = plain_keys[sol]

    if rebus:
        xd.set_header('Rebus', xdfile.REBUS_SEP.join(
            "%s=%s" % (k, v) for k, v in sorted(rebus.items(), key=lambda kv: (len(kv[0]), kv[0]))))

    xd.grid = ["".join(row) for row in puzzle]

    # words: id -> list of (row, col)
    crossword = _find(rect, 'crossword')
    words = {}
    for word in _children(crossword, 'word'):
        cells = []
        if 'x' in word.attrib and 'y' in word.attrib:
            cells = _word_cells(word.attrib['x'], word.attrib['y'])
        for sub in _children(word, 'cells'):
            cells.extend(_word_cells(sub.attrib['x'], sub.attrib['y']))
        words[word.attrib['id']] = cells

    # clues
    standard_numbers = None  # for puzzles published without clue numbers
    unclued = 0
    for clues in _children(crossword, 'clues'):
        title_el = _children(clues, 'title')
        title = _text(title_el[0]) if title_el else ''
        letters = "".join(ch for ch in title.upper() if ch in string.ascii_uppercase)
        if letters[:1] not in ('A', 'D'):
            warn("%s: clue list %r is not Across/Down; not a crossword" % (filename, title))
            return None
        direction = letters[0]

        for clue in _children(clues, 'clue'):
            word_id = clue.attrib.get('word')
            cells = words.get(word_id, [])
            numstr = clue.attrib.get('number', '').strip()
            if numstr.isdigit():
                number = int(numstr)
            elif not numstr and cells:
                if standard_numbers is None:
                    standard_numbers = _standard_numbers(xd.grid)
                number = standard_numbers.get(cells[0])
                if number is None:
                    warn("%s: %s clue %r starts at (%d,%d), which starts no slot" % (
                        filename, title, _text(clue), cells[0][1] + 1, cells[0][0] + 1))
                    continue
            else:
                warn("%s: %s clue %r has number %r" % (filename, title, _text(clue), numstr))
                continue
            if number == 0:
                # Crossword Compiler's marker for an entry with no clue
                unclued += 1
                continue
            text = _text(clue)
            answer = "".join(solutions.get(rc, '') for rc in cells)
            if not answer:
                warn("%s: no answer for %s%d" % (filename, direction, number))
            xd.clues.append(((direction, number), text, answer))

    if standard_numbers is not None:
        xd.notes += ("\nThe puzzle was published without clue numbers; "
                     "the numbers here follow standard crossword numbering.\n")
    if black_letters:
        warn("%s: %d letters printed in black squares moved to the notes" % (
            filename, len(black_letters)))
        xd.notes += ("\nIn the published grid these black squares contained letters: "
                     + "; ".join(_black_letter_runs(black_letters)) + ".\n")
    xd.notes = xd.notes.lstrip("\n")
    if unclued:
        warn("%s: %d unclued entries (clue number 0) dropped" % (filename, unclued))

    return xd


def _black_letter_runs(black_letters):
    """describe lettered black squares as runs along a row, e.g.
    'row 10, columns 16-21: SMILEY'; a lone square is 'row 4, column 5: I'"""
    runs = []
    for (y, x), ch in sorted(black_letters.items()):
        if runs and runs[-1][0] == y and runs[-1][2] == x - 1:
            runs[-1][2] = x
            runs[-1][3] += ch
        else:
            runs.append([y, x, x, ch])
    out = []
    for y, x0, x1, letters in runs:
        if x0 == x1:
            out.append("row %d, column %d: %s" % (y + 1, x0 + 1, letters))
        else:
            out.append("row %d, columns %d-%d: %s" % (y + 1, x0 + 1, x1 + 1, letters))
    return out


def _standard_numbers(grid):
    """standard crossword numbering: (row, col) -> number for each cell that
    starts an across or down slot of two or more cells"""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    def is_cell(r, c):
        return 0 <= r < rows and 0 <= c < cols and grid[r][c] not in xdfile.NON_ANSWER_CHARS

    numbers = {}
    n = 0
    for r in range(rows):
        for c in range(cols):
            if not is_cell(r, c):
                continue
            starts_across = not is_cell(r, c - 1) and is_cell(r, c + 1)
            starts_down = not is_cell(r - 1, c) and is_cell(r + 1, c)
            if starts_across or starts_down:
                n += 1
                numbers[(r, c)] = n
    return numbers


def _word_cells(xs, ys):
    """cells of a word from CC's x/y attrs, each a number or an inclusive range 'a-b'"""
    def span(s):
        if '-' in s:
            a, b = (int(n) for n in s.split('-'))
            return list(range(a, b + 1))
        return [int(s)]
    return [(y - 1, x - 1) for y in span(ys) for x in span(xs)]


if __name__ == "__main__":
    xdfile.main_parse(parse_ccxml)
