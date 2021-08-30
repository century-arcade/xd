#!/usr/bin/env python3

import sys
import string
import urllib.parse

# pip install crossword puzpy

import puz
import crossword


REBUS_SEP = " "
UNKNOWN_CHAR = '.'
BLOCK_CHAR = '#'
OPEN_CHAR = '_'
EOL = '\n'
SECTION_SEP = EOL + EOL
HEADER_ORDER = ['title', 'author', 'editor', 'copyright', 'number', 'date',
                'relation', 'special', 'rebus', 'cluegroup', 'description', 'notes']

NON_ANSWER_CHARS = [BLOCK_CHAR, OPEN_CHAR]  # UNKNOWN_CHAR is a wildcard answer character


def decode(s):
    s = s.replace('\x92', "'")
    s = s.replace('\xc2\x92', "'")
    s = s.replace('\xc3\x82',"")
    s = s.replace('\xc3\xa8',"è") # +A5. Crème de la crème ~ ELITE
    s = s.replace('\xe0','à') # -A49. Do the seemingly impossible, à la Jesus ~ WALKONWATER
    s = s.replace('\xc2', " ") # Change rest of 0xC2 to 0x20
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


class xdfile:
    def __init__(self):
        self.headers = {}  # [key] -> value or list of values
        self.grid = []  # list of string rows
        self.clues = []  # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""

    def cell(self, r, c):
        if r < 0 or c < 0 or r >= len(self.grid) or c >= len(self.grid[0]):
            return BLOCK_CHAR
        return self.grid[r][c]

    def rebus(self):
        """returns rebus dict of only special (non A-Z) characters"""
        rebusstr = self.get_header("Rebus")
        r = {}
        if rebusstr:
            for p in rebusstr.split(REBUS_SEP):
                cellchar, _, replstr = p.partition("=")
                assert len(cellchar) == 1, (rebusstr, cellchar)
                replstr = replstr.strip()
                r[cellchar] = replstr

        return r

    # generates: "A" or "D", clue_num, answer, r, c
    def iteranswers_full(self):
        # construct rebus dict with all grid possibilities so that answers are complete
        rebus = {}
        for c in string.ascii_letters:
            assert c not in rebus, c
            rebus[c] = c.upper()
        rebus.update(self.rebus())

        # traverse grid and yield (dir, pos, answer)
        clue_num = 1

        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                # compute number shown in box
                new_clue = False
                if self.cell(r, c - 1) in NON_ANSWER_CHARS:  # across clue start
                    ncells = 0
                    answer = ""
                    while self.cell(r, c + ncells) not in NON_ANSWER_CHARS:
                        cellval = self.cell(r, c + ncells)
                        answer += rebus.get(cellval, cellval)
                        ncells += 1

                    if ncells > 1:
                        new_clue = True
                        yield "A", clue_num, answer, r, c

                if self.cell(r - 1, c) in NON_ANSWER_CHARS:  # down clue start
                    ncells = 0
                    answer = ""
                    while self.cell(r + ncells, c) not in NON_ANSWER_CHARS:
                        cellval = self.cell(r + ncells, c)
                        answer += rebus.get(cellval, cellval)
                        ncells += 1

                    if ncells > 1:
                        new_clue = True
                        yield "D", clue_num, answer, r, c

                if new_clue:
                    clue_num += 1

    def width(self):
        return self.grid and len(self.grid[0]) or 0

    def height(self):
        return len(self.grid)

    # returns (w, h)
    def size(self):
        return (self.width(), self.height())

    def iteranswers(self):
        for direction, clue_num, answer, r, c in self.iteranswers_full():
            yield direction, clue_num, answer

    def set_header(self, fieldname, newvalue=None):
#        if fieldname in self.headers:
#            if newvalue != self.headers.get(fieldname, None):
#                log("%s[%s] '%s' -> '%s'" % (self.filename, fieldname, self.headers[fieldname], newvalue))

        if newvalue:
            newvalue = str(newvalue).strip()
            newvalue = " ".join(newvalue.splitlines())
            newvalue = newvalue.replace("\t", "  ")

            self.headers[fieldname] = newvalue
        else:
            if fieldname in self.headers:
                del self.headers[fieldname]

    def get_header(self, fieldname):
        v = self.headers.get(fieldname)
        assert v is None or isinstance(v, str), v
        return (v or "").strip()

    def iterheaders(self):
        def header_sort_key(item):
            if item[0].lower() not in HEADER_ORDER:
                return 1000

            return HEADER_ORDER.index(item[0].lower())

        for k, v in sorted(list(self.headers.items()), key=header_sort_key):
            yield k, v

    def to_unicode(self, emit_clues=True):
        # headers (section 1)

        r = ""

        if self.headers:
            for k, v in self.iterheaders():
                assert isinstance(v, str), v

                r += "%s: %s" % (k, v)
                r += EOL
        else:
            r += "Title: %s" % parse_pathname(self.filename).base
            r += EOL

        r += SECTION_SEP

        # grid (section 2)
        r += EOL.join(self.grid)
        r += EOL + EOL + EOL

        # clues (section 3)
        if emit_clues:
            prevdir = None
            for pos, clue, answer in self.clues:
                if not answer:
                    r += EOL
                    continue

                cluedir, cluenum = pos
                if prevdir and prevdir != cluedir: # Blank line between cluedirs
                    r += EOL
                prevdir = cluedir

                r += "%s%s. %s ~ %s" % (cluedir, cluenum, (clue or "[XXX]").strip(), answer)
                r += EOL

            if self.notes:
                r += EOL + EOL
                r += self.notes

        r += EOL

        # some Postscript CE encodings can be caught here
        r = r.replace('\x91', "'")
        r = r.replace('\x92', "'")
        r = r.replace('\x93', '"')
        r = r.replace('\x94', '"')
        r = r.replace('\x96', '___')
        r = r.replace('\x85', '...')

        # these are always supposed to be double-quotes
        r = r.replace("''", '"')

        return r


def parse_puz(contents, filename):
    rebus_shorthands = list("zyxwvutsrqponmlkjihgfedcba⚷⚳♇♆⛢♄♃♂♁♀☿♹♸♷♶♵♴♳⅘⅗⅖⅕♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠+&%$@?*0987654321")

    try:
        puzobj = puz.load(contents)
        puzzle = crossword.from_puz(puzobj)
    except puz.PuzzleFormatError as e:
        emsg = e.message
        if "<html>" in contents.decode('utf-8').lower():
            emsg += " (looks like html)"
        raise Exception(emsg)

    grid_dict = dict(list(zip(string.ascii_uppercase, string.ascii_uppercase)))

    xd = xdfile()

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

            rebustr = REBUS_SEP.join([("%s=%s" % (k, v)) for k, v in sorted(rebus.items())])
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
                rowstr += BLOCK_CHAR
            elif cell.solution == puzzle.block:
                rowstr += BLOCK_CHAR
            elif cell.solution == ':':
                rowstr += OPEN_CHAR
            elif cell == puzzle.empty:
                rowstr += UNKNOWN_CHAR
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
                raise Exception("Clue number doesn't match grid: %s" % cluenum)
            xd.clues.append((("A", number), decode(clue), answers.get(cluenum, "")))

        for number, clue in puzzle.clues.down():
            cluenum = "D" + str(number)
            if cluenum not in answers:
                raise Exception("Clue doesn't match grid: %s" % cluenum)
            xd.clues.append((("D", number), decode(clue), answers.get(cluenum, "")))
    except KeyError as e:
        raise Exception("Clue doesn't match grid: %s" % e)

    return xd


def main(fn):
    xd = parse_puz(open(fn, mode='rb').read(), fn)
    print(xd.to_unicode())


for fn in sys.argv[1:]:
    main(fn)
