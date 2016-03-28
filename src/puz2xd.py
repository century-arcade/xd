#!/usr/bin/env python
# -*- coding: utf-8 

# pip install crossword puzpy

import string
import puz
import crossword
import xdfile

import urllib

def reparse_date(s):
    import time
    tm = time.strptime(s, "%B %d, %Y")
    return time.strftime("%Y-%m-%d", tm)

def decode(s):
    s = s.replace(u'\x92', "'")
    s = s.replace(u'\x93', '"')
    s = s.replace(u'\x94', '"')
    s = s.replace(u'\x85', '...')
    s = urllib.unquote(s)
    return s

def is_block(puz, x, y):
    return x < 0 or y < 0 or x >= puz.width or y >= puz.height or puz[x, y].solution == '.'

def parse_puz(contents, filename):
    rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

    if not filename.lower().endswith('.puz'):
        return

    puzobj = puz.load(contents)

    puzzle = crossword.from_puz(puzobj)

    grid_dict = dict(zip(string.uppercase, string.uppercase))

    xd = xdfile.xdfile()
    xd.filename = filename

    xd.set_header("Author", puzobj.author)
    xd.set_header("Copyright", puzobj.copyright)
    xd.set_header("Notes", puzobj.notes)
    xd.set_header("Postscript", puzobj.postscript)
    xd.set_header("Preamble", puzobj.preamble)

    xd.set_header("Title", puzobj.title)

    rebus = { }
    r = puzobj.rebus()
    if r.has_rebus():
        for pair in puzobj.extensions["RTBL"].split(";"):
            pair = pair.strip()
            if not pair: continue
            k, v = pair.split(":")
            rebus[k] = v

        rebustr = " ".join([("%s=%s" % (k, v)) for k, v in sorted(rebus.items())])
        xd.set_header("Rebus", rebustr)

    for r, row in enumerate(puzzle):
        rowstr = ""
        for c, cell in enumerate(row):
            if puzzle.block is None and cell.solution == '.':
                rowstr += xdfile.BLOCK_CHAR
            elif puzzle.block == cell.solution:
                rowstr += xdfile.BLOCK_CHAR
            elif cell == puzzle.empty:
                rowstr += "."
            else:
                n = r * puzobj.width + c
                reb = puzobj.rebus()
                if reb.has_rebus() and n in reb.get_rebus_squares():
                    c = str(reb.table[n] - 1)
                    rowstr += c
                    cell.solution = rebus[c]
                else:
                    if cell.solution not in grid_dict:
#                        grid_dict[cell.solution] = rebus_shorthands.pop()
                        print " odd character '%s'" % cell.solution
                        rowstr += cell.solution
                    else:
                        rowstr += grid_dict[cell.solution]

        xd.grid.append(rowstr)


    # clues

    answers = { }
    clue_num = 1

    for r, row in enumerate(xd.grid):
        for c, cell in enumerate(row):
                # compute number shown in box
                new_clue = False
                if is_block(puzzle, c-1, r):  # across clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c+j, r):
                        answer += puzzle[c+j, r].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["A"+str(clue_num)] = answer

                if is_block(puzzle, c, r-1):  # down clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c, r+j):
                        answer += puzzle[c, r+j].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["D"+str(clue_num)] = answer

                if new_clue:
                    clue_num += 1

    for number, clue in puzzle.clues.across():
        xd.clues.append((("A", number), decode(clue), answers["A"+str(number)]))

    for number, clue in puzzle.clues.down():
        xd.clues.append((("D", number), decode(clue), answers["D"+str(number)]))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_puz)

