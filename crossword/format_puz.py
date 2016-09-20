# -*- coding: utf-8 -*-
import collections

from puz import Puzzle

from crossword import CrosswordException
from crossword.compat import range
from crossword.core import Crossword


def from_puz(puzzle):
    known_keys = (
        "width",
        "height",
        "author",
        "copyright"
        "title",
        "clues",
        "solution",
    )
    result = Crossword(puzzle.width, puzzle.height)
    result._format_identifier = Crossword.PUZ
    result.meta.creator = puzzle.author
    result.meta.rights = puzzle.copyright
    result.meta.title = puzzle.title
    result.block = '.'

    rows = []
    for i in range(0, len(puzzle.solution), puzzle.width):
        rows.append(puzzle.solution[i:i + puzzle.width])

    def is_across(x, y):
        if result[x, y].solution in ':.':
            return False
        start = x == 0 or (0 <= x - 1 and result[x - 1, y].solution in ':.')
        end = (x + 1 < puzzle.width and result[x + 1, y].solution not in ':.')
        return start and end

    def is_down(x, y):
        if result[x, y].solution in ':.':
            return False
        start = y == 0 or (y - 1 >= 0 and result[x, y - 1].solution in ':.')
        end = (y + 1 < puzzle.height and result[x, y + 1].solution not in ':.')
        return start and end

    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            result[x, y].cell = None
            result[x, y].solution = cell

    clue_index = 0
    number = 0
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            is_xy_across = is_across(x, y)
            is_xy_down = is_down(x, y)
            if is_xy_across or is_xy_down:
                number += 1
            if is_xy_across:
                result.clues.across[number] = puzzle.clues[clue_index]
                clue_index += 1
            if is_xy_down:
                result.clues.down[number] = puzzle.clues[clue_index]
                clue_index += 1

    for attr in dir(puzzle):
        if attr in known_keys:
            continue
        if attr.startswith('__'):
            continue
        if callable(getattr(puzzle, attr)):
            continue
        result._format[attr] = getattr(puzzle, attr)

    return result


def to_puz(crossword):
    result = Puzzle()
    result.width = crossword.width
    result.height = crossword.height
    result.author = crossword.meta.creator
    result.copyright = crossword.meta.rights
    result.title = crossword.meta.title

    cells = []
    for row in crossword:
        for cell in row:
            value = None
            if cell.solution is None:
                value = crossword.block if crossword.block else '.'
            else:
                value = cell.solution
            cells.append(value)
    result.solution = ''.join(cells)

    result.clues = []
    clues = collections.defaultdict(list)
    try:
        for number, clue in crossword.clues.across(sort=int):
            clues[number].append(clue)
    except ValueError:
        raise CrosswordException
    try:
        for number, clue in crossword.clues.down(sort=int):
            clues[number].append(clue)
    except ValueError:
        raise CrosswordException
    for number, clues in sorted(clues.items()):
        for clue in clues:
            result.clues.append(clue)

    if crossword._format_identifier == Crossword.PUZ:
        for key, value in crossword._format.items():
            setattr(result, key, value)

    return result
