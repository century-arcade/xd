#!/usr/bin/env python

import os
import re
import json
from urllib.parse import unquote

from . import xdfile

POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright']

def parse_ujson(content, filename):
    json_data = json.loads(content)

    # init crossword
    rows = int(json_data['Height'])
    xd = xdfile.xdfile()

    # add meta data
    for item in POSSIBLE_META_DATA:
        text = json_data.get(item, None)
        if text:
            xd.headers.append((item, unquote(text).decode("utf-8")))

    # add puzzle
    for row in range(1, rows + 1):
        line = json_data['Solution']['Line' + str(row)]
        xd.grid.append("".join(line.replace(' ', xdfile.BLOCK_CHAR)))

    # add clues
    layout = json_data['Layout']
    for clue_type in ('Across', 'Down'):
        for clue in json_data[clue_type + 'Clue'].split(os.linesep):
            number, text = clue.split('|')
            solution = _get_solution(number, clue_type[0], layout, xd.grid)
            xd.clues.append(((clue_type[0],
                            int(number)),
                            unquote(text).decode("utf-8").strip(),
                            solution))
            assert solution

    return xd


def _get_solution(number, direction, layout, puzzle):
    x, y = (-1, -1)
    for row in range(1, len(puzzle) + 1):
        line = layout['Line' + str(row)]
        try:
            pairs = re.findall('..', line)
            x = pairs.index(number)
            y = row - 1
            break
        except ValueError:
            pass

    # read puzzle text from (x,y) in the given direction
    # until we hit a block
    text = ''
    if direction == 'A':
        try:
            x_limit = puzzle[y].index(xdfile.BLOCK_CHAR, x)
        except ValueError:
            x_limit = len(puzzle[y])
        text = ''.join(puzzle[y][x:x_limit])
    elif direction == 'D':
        for row in range(y, len(puzzle)):
            char = puzzle[row][x]
            if char == xdfile.BLOCK_CHAR:
                break
            text += char
    return text

if __name__ == "__main__":
    xdfile.main_parse(parse_ujson)
