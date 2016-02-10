import os
import json

from crossword import Clue
from crossword import Constants
from crossword import Crossword
from utils import URLUtils
from utils import DateUtils
from errors import ContentDownloadError
from errors import NoCrosswordError


class denverpost(object):
    FILENAME_PREFIX = 'denverpost'
    RAW_CONTENT_TYPE = 'json'
    DAILY_PUZZLE_URL = 'https://embed.universaluclick.com/c/den/l/U2FsdGVkX1%%2FzdjyNCxD2oIjmBu5RQ2D0u3CYiGzfbDYhqyd3VDCsDPrMqAftBRF3%%0ArR9LLkAVhk4jtszeUlje4aAmlc6Vsu1yjJPHlBqtF0k%%3D/g/fcx/d/%s/data.json'
    DATE_FORMAT = '%Y-%m-%d'

    POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright']

    def get_content(self, date):
        date = DateUtils.to_string(date, denverpost.DATE_FORMAT)
        url = denverpost.DAILY_PUZZLE_URL %date
        try:
            content = URLUtils.get_content(url)
        except ContentDownloadError:
            raise NoCrosswordError('Date: %s; URL: %s' %(date, url))
        return content

    def build_crossword(self, content):
        json_data = json.loads(content)

        # init crossword
        rows = int(json_data['Height'])
        cols = int(json_data['Width'])
        crossword = Crossword(rows, cols)

        # add meta data
        for item in denverpost.POSSIBLE_META_DATA:
            text = json_data.get(item, None)
            if text:
                crossword.add_meta_data('%s: %s' %(item, text))

        # add puzzle
        puzzle = crossword.puzzle
        for row in range(1, rows+1):
            line = json_data['Solution']['Line'+str(row)]
            puzzle[row-1] = list(line.replace(' ', Constants.BLOCK_CHAR))
        crossword.set_puzzle(puzzle)

        # add clues
        layout = json_data['Layout']
        clue_types = ('Across', 'Down')
        for clue_type in clue_types:
            for clue in json_data[clue_type + 'Clue'].split(os.linesep):
                number, text = clue.split('|')
                type = getattr(Constants, clue_type.upper())
                solution = self._get_solution(number, type, layout, puzzle)
                crossword.add_clue(Clue(int(number), type, text, solution))

        return crossword

    def _get_solution(self, number, type, layout, puzzle):
        def get_number_location(number):
            x, y = (-1, -1)
            for row in range(1, len(puzzle)+1):
                line = layout['Line'+str(row)]
                try:
                    x = line.index(number) / 2
                    y = row - 1
                    break;
                except ValueError:
                    pass
            return (x, y)

        def get_text(x, y, direction):
            # read puzzle text from (x,y) in the given direction
            # until we hit a block
            text = ''
            if direction == Constants.ACROSS:
                try:
                    x_limit = puzzle[y].index(Constants.BLOCK_CHAR, x)
                except ValueError:
                    x_limit = len(puzzle[y])
                text = ''.join(puzzle[y][x:x_limit])
            elif direction == Constants.DOWN:
                for row in range(y, len(puzzle)):
                    char = puzzle[row][x]
                    if char == Constants.BLOCK_CHAR:
                        break
                    text += char
            return text

        x, y = get_number_location(number)
        return get_text(x, y, type)
