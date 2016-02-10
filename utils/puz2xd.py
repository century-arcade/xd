#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
import sys
import string
import crossword
import puz

EOL = '\n'

rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

rebus_longhands = {
        'NINE': '9',
        'EIGHT': '8',
        'SEVEN': '7',
        'SIX': '6',
        'FIVE': '5',
        'FOUR': '4',
        'THREE': '3',
        'TWO': '2',
        'ONE': '1',
        'ZERO': '0',
        'AUGHT': '0',
        'AMPERSAND': '&',
        'AND': '&',
        'ASTERISK': '*',
        'PERCENT': '%',
        'STAR': '*',
        'AT': '@',
        'DOLLAR': '$',
        'PLUS': '+',
        'CENT': 'c',
#        'DASH': '-',
#        'DOT': '●',
}

def is_block(puz, x, y):
    return x < 0 or y < 0 or x >= puz.width or y >= puz.height or puz[x, y].solution == '.'

def puz2xd(fn):
    puz_object = puz.read(fn)
    puzzle = crossword.from_puz(puz_object)

    grid_dict = dict(zip(string.uppercase, string.uppercase))

    out = ""

    for k, v in puzzle.meta():
        if v:
            k = k[0].upper() + k[1:].lower()
            out += "%s: %s" % (k, v) + EOL

    out += EOL + EOL

    answers = { }
    clue_num = 1

    for r, row in enumerate(puzzle):
        rowstr = " "
        for c, cell in enumerate(row):
            if puzzle.block is None and cell.solution == '.':
                rowstr += "#"
            elif puzzle.block == cell.solution:
                rowstr += "#"
            elif cell == puzzle.empty:
                rowstr += "."
            else:
                if cell.solution not in grid_dict:
                    grid_dict[cell.solution] = rebus_shorthands.pop()

                rowstr += grid_dict[cell.solution]

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
                
        out += rowstr + EOL

    out += EOL + EOL

    for number, clue in puzzle.clues.across():
        out += "A%s. %s ~ %s" % (number, clue, answers["A"+str(number)]) + EOL

    out += EOL

    for number, clue in puzzle.clues.down():
        out += "D%s. %s ~ %s" % (number, clue, answers["D"+str(number)]) + EOL

    out += EOL + EOL

#    out += puzzle.notes
#
#    out += EOL + EOL

    return out

for fn in sys.argv[1:]:
    base, ext = os.path.splitext(fn)
    file(base+".xd", 'w').write(puz2xd(fn).encode("utf-8"))

