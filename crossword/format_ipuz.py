# -*- coding: utf-8 -*-
from crossword.core import Crossword, CrosswordCell
from crossword.exceptions import CrosswordException


def from_ipuz(ipuz_dict):
    for kind in ipuz_dict['kind']:
        if not kind.startswith("http://ipuz.org/crossword"):
            raise CrosswordException

    known_keys = (
        "dimensions",
        "editor",
        "author",
        "date",
        "notes",
        "uniqueid",
        "publisher",
        "copyright",
        "title",
        "block",
        "empty",
        "clues",
        "puzzle",
        "solution",
    )
    crossword = Crossword(
        ipuz_dict['dimensions']['width'],
        ipuz_dict['dimensions']['height']
    )
    crossword._format_identifier = Crossword.IPUZ
    crossword.meta.contributor = ipuz_dict.get('editor')
    crossword.meta.creator = ipuz_dict.get('author')
    crossword.meta.date = ipuz_dict.get('date')
    crossword.meta.description = ipuz_dict.get('notes')
    crossword.meta.identifier = ipuz_dict.get('uniqueid')
    crossword.meta.publisher = ipuz_dict.get('publisher')
    crossword.meta.rights = ipuz_dict.get('copyright')
    crossword.meta.title = ipuz_dict.get('title')
    crossword.block = ipuz_dict.get('block')
    crossword.empty = ipuz_dict.get('empty')

    for number, clue in ipuz_dict.get('clues', {}).get('Across', []):
        crossword.clues.across[number] = clue
    for number, clue in ipuz_dict.get('clues', {}).get('Down', []):
        crossword.clues.down[number] = clue

    for x, y in crossword.cells:
        crossword[x, y] = CrosswordCell()

    for key in ('puzzle', 'solution'):
        entry = ipuz_dict.get(key)
        for x, y in crossword.cells:
            try:
                crossword[x, y][key] = entry[y][x]
            except (IndexError, TypeError):
                crossword[x, y][key] = None

    for key, value in ipuz_dict.items():
        if key not in known_keys:
            crossword._format[key] = value

    return crossword


def to_ipuz(crossword):
    ipuz_dict = {
        "version": "http://ipuz.org/v1",
        "dimensions": {
            "width": crossword.width,
            "height": crossword.height,
        },
        "puzzle": [
            [getattr(cell, "puzzle", None) for cell in row]
            for row in crossword._data
        ],
        "solution": [
            [getattr(cell, "solution", None) for cell in row]
            for row in crossword._data
        ],
    }
    if crossword.meta.creator is not None:
        ipuz_dict["author"] = crossword.meta.creator
    if crossword.meta.rights is not None:
        ipuz_dict["copyright"] = crossword.meta.rights
    if crossword.meta.date is not None:
        ipuz_dict["date"] = crossword.meta.date
    if crossword.meta.contributor is not None:
        ipuz_dict["editor"] = crossword.meta.contributor
    if crossword.meta.description is not None:
        ipuz_dict["notes"] = crossword.meta.description
    if crossword.meta.publisher is not None:
        ipuz_dict["publisher"] = crossword.meta.publisher
    if crossword.meta.identifier is not None:
        ipuz_dict["uniqueid"] = crossword.meta.identifier
    if crossword.meta.title is not None:
        ipuz_dict["title"] = crossword.meta.title
    if crossword.block is not None:
        ipuz_dict["block"] = crossword.block
    if crossword.empty is not None:
        ipuz_dict["empty"] = crossword.empty

    across_clues = [list(item) for item in crossword.clues.across()]
    down_clues = [list(item) for item in crossword.clues.down()]
    if across_clues or down_clues:
        ipuz_dict["clues"] = {}
        if across_clues:
            ipuz_dict["clues"]['Across'] = across_clues
        if down_clues:
            ipuz_dict["clues"]['Down'] = down_clues

    if crossword._format_identifier == Crossword.IPUZ:
        ipuz_dict.update(crossword._format)
    return ipuz_dict
