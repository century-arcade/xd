#!/usr/bin/env python3
# -*- coding: utf-8

import string
import operator
import functools
import re
import datetime

from .utils import parse_pathname, parse_tsv, progress, parse_pubid, find_files, get_args, memoize, parse_xdid

g_corpus = []  # list of xdfile
g_all_clues = []  # list of ClueAnswer


class Error(Exception):
    pass


class IncompletePuzzleParse(Error):
    """Error while parsing source puzzle"""
    def __init__(self, xd, msg=""):
        Error.__init__(self, msg)
        self.xd = xd


class PuzzleParseError(Error):
    pass


class NoShelfError(Error):
    pass


REBUS_SEP = " "


UNKNOWN_CHAR = '.'
BLOCK_CHAR = '#'
OPEN_CHAR = '_'
NON_ANSWER_CHARS = [BLOCK_CHAR, OPEN_CHAR]  # UNKNOWN_CHAR is a wildcard answer character
EOL = '\n'
SECTION_SEP = EOL + EOL
HEADER_ORDER = ['title', 'author', 'editor', 'copyright', 'number', 'date',
                'relation', 'special', 'rebus', 'cluegroup', 'description', 'notes']


class xdfile:
    def __init__(self, xd_contents=None, filename=None, pubid=None):
        self.filename = filename
        self.headers = {}  # [key] -> value or list of values
        self.grid = []  # list of string rows
        self.clues = []  # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""

        if filename:
            self._publication_id = pubid or parse_pubid(filename)
        else:
            self._publication_id = pubid

        if not self._publication_id:
            raise Error("No Publication Id in '%s'" % filename)

        if xd_contents:
            self.parse_xd(xd_contents)

    def __str__(self):
        return self.filename or "<unknown xd puzzle>"

    def width(self):
        return self.grid and len(self.grid[0]) or 0

    def height(self):
        return len(self.grid)

    # returns (w, h)
    def size(self):
        return (self.width(), self.height())

    def xdid(self):
        num = self.get_header("Number")
        if num:
            return '%s-%03d' % (self._publication_id, int(num))

        assert self.date()
        return '%s%s' % (self._publication_id, self.date())

    def date(self):
        dt = self.get_header("Date")
        if not dt and self._publication_id:
            dt = parse_pathname(self.filename).base[len(self._publication_id):]
        return dt

    def year(self):
        return self.date().split('-')[0]

    def publication_id(self):  # "nyt"
        return self._publication_id

    def iterdiffs(self, other):
        for k in set(self.headers.keys()) | set(other.headers.keys()):
            if self.get_header(k) != other.get_header(k):
                yield self.get_header(k), other.get_header(k)

        for a, b in zip(self.grid, other.grid):
            if a != b:
                yield a, b

        for a, b in zip(self.clues, other.clues):
            if a != b:
                yield a, b

    def diffs(self, other):
        return [(a, b) for a, b in self.iterdiffs(other)]

    def get_header(self, fieldname):
        v = self.headers.get(fieldname)
        assert v is None or isinstance(v, str), v
        return (v or "").strip()

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

    def add_header(self, fieldname, value):
        if fieldname in self.headers:
            assert type(self.headers[fieldname]) == list
            self.headers[fieldname].append(value)
        else:
            self.headers[fieldname] = [value]

    def get_clue_for_answer(self, target):
        clues = []
        for pos, clue, answer in self.clues:
            if answer == target:
                clues.append(clue)

        if not clues:
            return None

        assert len(clues) == 1, Exception("multiple clues for %s: %s" % (target, " | ".join(clues)))
        return clues[0]

    def get_clue(self, clueid):
        for pos, clue, answer in self.clues:
            posdir, n = pos
            if clueid == posdir + str(n):
                return clue

    def append_clue_break(self):
        self.clues.append((("", ""), "", ""))

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

    def iterclues(self):
        for pos, clue, answer in self.clues:
            if answer:  # skip cluegroup breaks
                yield "%s%s" % pos, clue, answer

    def iteranswers(self):

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
                        yield "A", clue_num, answer

                if self.cell(r - 1, c) in NON_ANSWER_CHARS:  # down clue start
                    ncells = 0
                    answer = ""
                    while self.cell(r + ncells, c) not in NON_ANSWER_CHARS:
                        cellval = self.cell(r + ncells, c)
                        answer += rebus.get(cellval, cellval)
                        ncells += 1

                    if ncells > 1:
                        new_clue = True
                        yield "D", clue_num, answer

                if new_clue:
                    clue_num += 1

    def get_answer(self, clueid):
        for pos, clue, answer in self.clues:
            posdir, n = pos
            if clueid == posdir + str(n):
                return answer

    def parse_xd(self, xd_contents):
        # placeholders, actual numbering starts at 1
        section = 0
        subsection = 0

        # fake blank line at top to allow leading actual blank lines before headers
        nblanklines = 2

        for line in xd_contents.splitlines():
            # leading whitespace is decorative
            line = line.strip()

            # collapse consecutive lines of whitespace into one line and start next group
            if not line:
                nblanklines += 1
                continue
            else:
                if nblanklines >= 2:
                    section += 1
                    subsection = 1
                    nblanklines = 0
                elif nblanklines == 1:
                    if section == 3:
                        self.append_clue_break()

                    subsection += 1
                    nblanklines = 0

            if section == 1:
                # headers first
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()

                    if k in self.headers:
                        if isinstance(self.headers[k], str):
                            self.headers[k] = [self.headers[k], v]
                        else:
                            self.headers[k].append(v)
                    else:
                        self.set_header(k, v)
                else:
                    self.notes += line + "\n"

            elif section == 2:
                assert self.headers, "no headers"
                # grid second
                self.grid.append(line)
            elif section == 3:
                # across or down clues
                answer_idx = line.rfind("~")
                if answer_idx > 0:
                    clue = line[:answer_idx]
                    answer = line[answer_idx + 1:]
                else:
                    clue, answer = line, ""

                clue_idx = clue.find(".")

                assert clue_idx > 0, "no clue number: " + clue
                pos = clue[:clue_idx].strip()
                clue = clue[clue_idx + 1:]

                try:
                    cluedir = pos[0]
                    cluenum = int(pos[1:])
                except:
                    cluedir = ""
                    cluenum = pos  # fallback to strings for non-numeric clue "numbers"
                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else:  # anything remaining
                if line:
                    self.notes += line + EOL


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

    def transpose(self):
        def get_col(g, n):
            return "".join([r[n] for r in g])

        flipxd = xdfile()
        flipxd.filename = self.filename + ".transposed"
        flipxd.headers = self.headers.copy()

        g = []
        for i in range(len(self.grid[0])):
            g.append(get_col(self.grid, i))

        flipxd.grid = g

        for posdir, posnum, answer in flipxd.iteranswers():
            clue = self.get_clue_for_answer(answer)
            if clue is None:  # '' might be the actual clue
                clue = '[XXX]'
            flipxd.clues.append(((posdir, posnum), clue, answer))

        flipxd.clues = sorted(flipxd.clues)
        return flipxd


# get_args(...) should be called before corpus()
@memoize
def corpus():
    from .utils import log

    args = get_args()

    ret = []

    for fullfn, contents in find_files(args.corpusdir, ext='.xd'):
        try:
            progress(fullfn)

            xd = xdfile(contents.decode("utf-8"), fullfn)

            ret.append(xd)
        except Exception as e:
            log(str(e))
            if args.debug:
                raise

    progress()

    return ret


# just xdid -> contents
@memoize
def corpus_contents():
    args = get_args()
    ret = {}
    for fullfn, contents in find_files(args.corpusdir, ext='.xd'):
        xdid = parse_xdid(fullfn)
        ret[xdid.lower()] = contents
    return ret


def year_from_date(dt):
    try:
        return int(dt.split('-')[0])
    except:
        return 0

def dow_from_date(dt):
    # Return day of week out of date
    try:
        return datetime.datetime.strptime(dt, '%Y-%m-%d').strftime('%a') 
    except:
        return None


class ClueAnswer:
    def __init__(self, pubid, dt, answer, clue):
        self.pubid = pubid
        self.date = dt
        self.answer = answer
        self.clue = clue

    def pubyear(self):
        return (self.pubid, year_from_date(self.date))

    def xdid(self):
        return self.pubid + self.date

    def __str__(self):
        return '[%s%s] %s' % (self.pubid, self.date, self.clue)


def clues():
    if not g_all_clues:
        for xd in corpus():  # r in parse_tsv("clues.tsv", "AnswerClue"):
            progress(xd.filename)
            pubid = xd.publication_id()
            dt = xd.date() or ""
            for pos, clue, answer in xd.iterclues():
                ca = ClueAnswer(pubid, dt, answer, clue)
                g_all_clues.append(ca)

        progress()

    return g_all_clues


def get_shelf(path):
    return parse_pathname(path).base.split('-')[0]

@memoize
def get_xd(xdid):
    xd = xdfile(corpus_contents()[xdid].decode("utf-8"), xdid)
    return xd

def num_cells(size):
    """
    Return grid size in cells out of Size definition e.g. "15X15R"
    """
    size_l = re.findall('\d+', size)
    return functools.reduce(operator.mul, [int(i) for i in size_l], 1)
