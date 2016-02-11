from os import linesep as EOL

from errors import ArgumentError


class Constants(object):
    ACROSS = 'A'
    DOWN = 'D'

    BLOCK_CHAR = '#'
    SOLUTION_SEPARATOR = '~'


class Crossword(object):
    def __init__(self, rows, cols):
        if not isinstance(rows, int) or rows <= 0:
            raise ArgumentError('Invalid Param: rows = %s' %rows)
        if not isinstance(cols, int) or cols <= 0:
            raise ArgumentError('Invalid Param: cols = %s' %cols)

        self.rows = rows
        self.cols = cols

        self.puzzle = [[Constants.BLOCK_CHAR for i in range(self.cols)]
                       for j in range(self.rows)]
        self.meta_data = []
        self.clues = {}
        self.clues[Constants.ACROSS] = []
        self.clues[Constants.DOWN] = []

    def is_valid(self):
        if len(self.puzzle) != self.rows:
            return False

        for row in self.puzzle:
            if len(row) != self.cols:
                return False
        return True

    def set_puzzle(self, puzzle):
        if not isinstance(puzzle, list) or len(puzzle) != self.rows:
            raise ArgumentError('Invalid Param: puzzle = %s' %puzzle)
        for row in puzzle:
            if not isinstance(row, list) or len(row) != self.cols:
                raise ArgumentError('Invalid Param: puzzle row = %s' %row)
        self.puzzle = puzzle

    def set_puzzle_row(self, row_num, data):
        if not isinstance(row_num, int) or row_num <= 0 or row_num >= self.rows:
            raise ArgumentError('Invalid Param: row_num = %s' %row_num)
        if not isinstance(data, list) or len(data) != self.cols:
            raise ArgumentError('Invalid Param: data = %s' %data)

        self.puzzle[row_num] = data

    def set_puzzle_col(self, col_num, data):
        if not isinstance(col_num, int) or col_num <= 0 or col_num >= self.cols:
            raise ArgumentError('Invalid Param: col_num = %s' %col_num)
        if not isinstance(data, list) or len(data) != self.rows:
            raise ArgumentError('Invalid Param: data = %s' %data)

        for i in range(len(data)):
            self.puzzle[i][col_num] = data[i]

    def add_meta_data(self, data):
        self.meta_data.append(data);

    def add_clue(self, clue):
        if not isinstance(clue, Clue):
            raise ArgumentError('Invalid Param: clue = %s' %clue)
        self.clues[clue.type].append(clue)

    def as_xd(self):
        xd_content = self._meta_data_as_string()
        xd_content += EOL + EOL
        xd_content += self._puzzle_as_string()
        xd_content += EOL + EOL
        xd_content += self._clues_as_string()
        xd_content += EOL + EOL
        return xd_content

    def _meta_data_as_string(self):
        return EOL.join(self.meta_data) + EOL

    def _clues_as_string(self, with_solution=True):
        string = ''
        if len(self.clues[Constants.ACROSS]):
            string += EOL.join(clue.as_string(with_solution)
                               for clue in self.clues[Constants.ACROSS])
            string += EOL + EOL

        if len(self.clues[Constants.DOWN]):
            string += EOL.join(clue.as_string(with_solution)
                               for clue in self.clues[Constants.DOWN])
            string += EOL
        return string.strip()

    def _puzzle_as_string(self):
        return EOL.join([''.join(row) for row in self.puzzle]) + EOL

    def __str__(self):
        return self.as_xd()


class Clue(object):
    VALID_TYPES = [Constants.ACROSS, Constants.DOWN]

    def __init__(self, number, type, text, solution=None, hint=None):
        if not isinstance(number, int) or number <= 0:
            raise ArgumentError('Invalid Param: number = %s' %number)
        if not isinstance(type, basestring) or type not in Clue.VALID_TYPES:
            raise ArgumentError('Invalid Param: type = %s' %type)

        self.number = number
        self.type = type.upper()
        self.id = '%s%s' %(type, number)
        self.text = text
        self.solution = solution
        self.hint = hint

    def as_string(self, with_solution=True):
        text = self.text
        if self.hint:
            text = '%s [Hint](%s)' %(text, self.hint)
        if with_solution and self.solution:
            text = '%s %s %s' %(text, Constants.SOLUTION_SEPARATOR, self.solution)
        return '%s. %s' %(self.id, text)

    def __str__(self):
        return self.as_string()

