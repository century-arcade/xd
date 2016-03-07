#!/usr/bin/env python
# -*- coding: utf-8 

# pip install crossword puzpy

import string
import puz
import crossword
import xdfile

hdr_renames = { "creator": "author", "rights": "copyright" }

hdr_order = [ "title", "author", "editor", "copyright", "publisher", "category", "description", "date" ]

rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

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

def parse_puz(contents):
    puz_object = puz.load(contents)
    puzzle = crossword.from_puz(puz_object)

    grid_dict = dict(zip(string.uppercase, string.uppercase))

    xd = xdfile.xdfile()

    md = dict([ (hdr_renames.get(k.lower(), k), v) for k, v in puzzle.meta() if v ])
    if " / " in md.get("author", ""):
        author, editor = md.get("author").split(" / ")
        editor = editor.strip()
        author = author.strip()
        author = author.lstrip("By ")
        editor = editor.lstrip("Edited by ")
        md["author"] = author
        md["editor"] = editor

    if "Washington Post" in md.get("copyright", ""):
        a = md["author"]
        if " - " in a:
            datestr, rest = a.split(" - ")
            md["date"] = reparse_date(datestr)
            if "By " in rest:
                md["title"], rest = rest.split(" By ")
            else:
                md["title"], rest = rest.split(" by ", 1)

            if "Edited by " in rest:
                md["author"], md["editor"] = rest.split(", Edited by ")
            elif "edited by " in rest:
                md["author"], md["editor"] = rest.split(", edited by ")
            else:
                md["author"] = rest

        md["copyright"] = md["copyright"].lstrip("Copyright")

    for k, v in sorted(md.items(), key=lambda x: hdr_order.index(x[0])):
        if v:
            k = k[0].upper() + k[1:].lower()
            v = decode(v.strip())
            v = v.replace(u"© ", "")
            xd.headers.append((k, v))

    answers = { }
    clue_num = 1

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
        xd.grid.append(rowstr)

    for number, clue in puzzle.clues.across():
        xd.clues.append((("A", number), decode(clue), answers["A"+str(number)]))

    for number, clue in puzzle.clues.down():
        xd.clues.append((("D", number), decode(clue), answers["D"+str(number)]))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_puz)

