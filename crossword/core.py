# -*- coding: utf-8 -*-
import collections
import os

from crossword.compat import basestring, range, str


class CrosswordCell(dict):

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError

    def __setattr__(self, name, value):
        self[name] = value


class CrosswordMetadata(dict):

    def __init__(self):
        super(CrosswordMetadata, self).__init__()

        # Dublin Core Metadata Element Set, Version 1.1
        self['contributor'] = None
        self['coverage'] = None
        self['creator'] = None
        self['date'] = None
        self['description'] = None
        self['format'] = None
        self['identifier'] = None
        self['language'] = None
        self['publisher'] = None
        self['relation'] = None
        self['rights'] = None
        self['source'] = None
        self['subject'] = None
        self['title'] = None
        self['type'] = None

    def __call__(self):
        for item in sorted(self.items()):
            yield item

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError

    def __setattr__(self, name, value):
        self[name] = value


class CrosswordDirectionClues(collections.OrderedDict):

    def __init__(self, *args, **kwargs):
        super(CrosswordDirectionClues, self).__init__(*args, **kwargs)

    def __call__(self, sort=int):
        if sort is not None:
            items = sorted(self.items(), key=lambda item: sort(item[0]))
        else:
            items = self.items()
        for item in items:
            yield item


class CrosswordClues(dict):

    ACROSS = 'across'

    DOWN = 'down'

    def __init__(self):
        super(CrosswordClues, self).__init__()
        self._directions = (CrosswordClues.ACROSS, CrosswordClues.DOWN)
        for direction in self._directions:
            self[direction] = CrosswordDirectionClues()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError

    def all(self, sort=int):
        for direction in self._directions:
            for number, clue in self[direction](sort=sort):
                yield direction, number, clue


class Crossword(object):

    IPUZ = "ipuz"

    PUZ = "puz"

    def __init__(self, width=15, height=15):
        if width <= 0:
            raise ValueError("Width needs to be at least one")
        if height <= 0:
            raise ValueError("Height needs to be at least one")
        self.width = width
        self.height = height
        self._data = [
            [CrosswordCell() for _ in range(width)] for _ in range(height)
        ]
        self.meta = CrosswordMetadata()
        self.clues = CrosswordClues()
        self._format_identifier = None  # file format-specific identifier
        self._format = {}  # file format-specific data
        self.block = None
        self.empty = None

    @property
    def cells(self):
        for y in range(self.height):
            for x in range(self.width):
                yield x, y

    @property
    def content(self):
        return {
            'width': self.width,
            'height': self.height,
            'cells': self._data,
            'metadata': self.meta,
            'clues': {
                'across': self.clues.across,
                'down': self.clues.down,
            },
            'block': self.block,
            'empty': self.empty,
            'type': self._format_identifier,
            'format': self._format,
        }

    def __getitem__(self, index):
        if isinstance(index, tuple):
            x, y = index
            if not (0 <= x < self.width):
                raise IndexError("Invalid cell coordinates: {}".format(index))
            if not (0 <= y < self.height):
                raise IndexError("Invalid cell coordinates: {}".format(index))
            return self._data[y][x]
        if not (0 <= index < self.height):
            raise IndexError("Invalid row coordinate: {}".format(index))
        return self._data[index]

    def __setitem__(self, index, value):
        x, y = index
        if isinstance(value, basestring):
            value = {'cell': value}
        if not isinstance(value, CrosswordCell):
            value = CrosswordCell(value)
        self._data[y][x] = value

    def __str__(self):
        result = []
        for row in self:
            for cell in row:
                result.append(str(cell if cell else ' '))
            result.append(str(os.linesep))
        return str('').join(result)
