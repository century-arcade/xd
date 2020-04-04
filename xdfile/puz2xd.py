#!/usr/bin/env python3
# -*- coding: utf-8

# pip install crossword puzpy

import string
import puz
import crossword
import urllib.request, urllib.parse, urllib.error
import time

import xdfile
from .utils import log, error, warn


def reparse_date(s):

    tm = time.strptime(s, "%B %d, %Y")
    return time.strftime("%Y-%m-%d", tm)


def decode(s):
    s = s.replace('\x92', "'")
    s = s.replace('\xc2\x92', "'")
    s = s.replace('\xc3\x82',"")
    s = s.replace('\xc3\xa8',"è") # +A5. Crème de la crème ~ ELITE
    s = s.replace('\xe0','à') # -A49. Do the seemingly impossible, à la Jesus ~ WALKONWATER
    s = s.replace('\xc2', " ") # Change rest ot 0xC2 to 0x20
    s = s.replace('\xa0'," ")
    s = s.replace('\x93', '"')
    s = s.replace('\x94', '"')
    s = s.replace('\x97', "—")
    s = s.replace('\x85', '...')
    s = s.replace('\x86', '†')
    s = s.replace('\xd3','"')
    s = s.replace('\xd4','"')
    s = urllib.parse.unquote(s)
    return s


def is_block(puz, x, y):
    return x < 0 or y < 0 or x >= puz.width or y >= puz.height or puz[x, y].solution == '.'


def parse_puz(contents, filename):
    rebus_shorthands = list("zyxwvutsrqponmlkjihgfedcba⚷⚳♇♆⛢♄♃♂♁♀☿♹♸♷♶♵♴♳⅘⅗⅖⅕♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠+&%$@?*0987654321")

    try:
        puzobj = puz.load(contents)
        puzzle = crossword.from_puz(puzobj)
    except puz.PuzzleFormatError as e:
        emsg = e.message
        if "<html>" in contents.decode('utf-8').lower():
            emsg += " (looks like html)"
        raise xdfile.PuzzleParseError(emsg)

    grid_dict = dict(list(zip(string.ascii_uppercase, string.ascii_uppercase)))

    xd = xdfile.xdfile('', filename)

    xd.set_header("Author", puzobj.author)
    xd.set_header("Copyright", puzobj.copyright)
    xd.set_header("Notes", puzobj.notes)
    xd.set_header("Postscript", "".join(x for x in puzobj.postscript if ord(x) >= ord(' ')))
    xd.set_header("Preamble", puzobj.preamble)

    xd.set_header("Title", puzobj.title)

    used_rebuses = {}  # [puz_rebus_gridvalue_as_string] -> our_rebus_gridvalue
    rebus = {}  # [our_rebus_gridvalue] -> full_cell
    r = puzobj.rebus()
    if r.has_rebus():
        grbs = puzobj.extensions[b"GRBS"]
        if sum(x for x in grbs if x != 0) > 0:   # check for an actual rebus
            for pair in puzobj.extensions[b"RTBL"].decode("cp1252").split(";"):
                pair = pair.strip()
                if not pair:
                    continue
                key, value = pair.split(":")
                rebuskey = rebus_shorthands.pop()
                used_rebuses[key] = rebuskey
                rebus[rebuskey] = decode(value)

            rebustr = xdfile.REBUS_SEP.join([("%s=%s" % (k, v)) for k, v in sorted(rebus.items())])
            xd.set_header("Rebus", rebustr)

    # check for circles and record them if they exist
    circles = []
    if b"GEXT" in puzobj.extensions: 
        for i, c in enumerate(puzobj.extensions[b"GEXT"]):
            if c == 0x80: circles.append(i)
    if circles: xd.set_header("Special", "circle")

    for r, row in enumerate(puzzle):
        rowstr = ""
        for c, cell in enumerate(row):
            if puzzle.block is None and cell.solution == '.':
                rowstr += xdfile.BLOCK_CHAR
            elif cell.solution == puzzle.block:
                rowstr += xdfile.BLOCK_CHAR
            elif cell.solution == ':':
                rowstr += xdfile.OPEN_CHAR
            elif cell == puzzle.empty:
                rowstr += xdfile.UNKNOWN_CHAR
            else:
                n = r * puzobj.width + c
                reb = puzobj.rebus()
                if reb.has_rebus() and n in reb.get_rebus_squares():
                    ch = str(reb.table[n] - 1)
                    rowstr += used_rebuses[ch]
                    cell.solution = rebus[used_rebuses[ch]]
                else:
                    ch = cell.solution
                    if ch not in grid_dict:
                        if ch in rebus_shorthands:
                            cellch = ch
                            rebus_shorthands.remove(ch)
                            warn("%s: unknown grid character '%s', assuming rebus of itself" % (filename, ch))
                        else:
                            cellch = rebus_shorthands.pop()
                            warn("%s: unknown grid character '%s', assuming rebus (as '%s')" % (filename, ch, cellch))

                        xd.set_header("Rebus", xd.get_header("Rebus") + " %s=%s" % (cellch, ch))

                        grid_dict[ch] = cellch
                    rowstr += grid_dict[ch].lower() if n in circles else grid_dict[ch]
                    # ^ assumes a cell is never rebus and circle.

        xd.grid.append(rowstr)

    assert xd.size() == (puzzle.width, puzzle.height), "non-matching grid sizes"

    # clues
    answers = {}

    for posdir, posnum, answer in xd.iteranswers():
        answers[posdir[0] + str(posnum)] = answer

    try:
        for number, clue in puzzle.clues.across():
            cluenum = "A" + str(number)
            if cluenum not in answers:
                raise xdfile.IncompletePuzzleParse(xd, "Clue number doesn't match grid: " + cluenum)
            xd.clues.append((("A", number), decode(clue), answers.get(cluenum, "")))

        # xd.append_clue_break()

        for number, clue in puzzle.clues.down():
            cluenum = "D" + str(number)
            if cluenum not in answers:
                raise xdfile.IncompletePuzzleParse(xd, "Clue doesn't match grid: " + cluenum)
            xd.clues.append((("D", number), decode(clue), answers.get(cluenum, "")))
    except KeyError as e:
        raise xdfile.IncompletePuzzleParse(xd, "Clue doesn't match grid: " + str(e))

    return xd

if __name__ == "__main__":
    import sys
    from utils import get_args, find_files

    args = get_args(desc='parse .puz files')
    for fn, contents in find_files(*sys.argv[1:]):
        xd = parse_puz(contents, fn)
        print(xd.to_unicode())

