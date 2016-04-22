#!/usr/bin/env python
# -*- coding: utf-8

from __future__ import print_function

from collections import namedtuple
import sys
import os
import re
import datetime
import string
import zipfile
import argparse

import utils

from utils import log, progress


class Error(Exception):
    pass


class UnknownFilenameFormat(Error):
    """Source filename format not known"""
    pass


class IncompletePuzzleParse(Error):
    """Error while parsing source puzzle"""
    def __init__(self, xd, msg=""):
        Error.__init__(self, msg)
        self.xd = xd


class PuzzleParseError(Error):
    pass


publishers = {
    'unk': 'unknown',
    'che': 'chronicle',
    'ch': 'chicago',
    'cs': 'crossynergy',
    'pp': 'wapost',
    'wsj': 'wsj',
    'rnr': 'rocknroll',
    'nw': 'newsday',
    'nyt': 'nytimes',
    'tech': 'nytimes',
    'tm': "time",
    'nfl': "cbs",
    'cn': "crosswordnation",
    'vwl': 'nytimes',
    'nyk': 'nytimes',
    'la': 'latimes',
    'nys': 'nysun',
    'pzz': 'puzzazz',
    'nyh': 'nyherald',
    'lt': 'london',
    'pa': 'nytimes',
    'pk': 'king',
    'nym': 'nymag',
    'db': 'dailybeast',
    'awm': 'threeacross',
    'rp': 'rexparker',
    'wp': 'wapost',
    'nl': 'lampoon',
    'tmdcr': 'tribune',
    'kc': 'kcstar',
    'mg': 'mygen',
    'atc': 'crossroads',
    'onion': 'onion',
    'mm': 'aarp',
    'ue': 'universal',
    'ut': 'universal',
    'up': 'universal',
    'us': 'universal',
    'um': 'universal',
    'ub': 'universal',
    'ss': 'simonschuster',
    'sl': 'slate',
    'ana': 'nytimes',
}


SEP = "\t"
REBUS_SEP = " "
g_args = None
g_currentProgress = None


UNKNOWN_CHAR = '.'
BLOCK_CHAR = '#'
OPEN_CHAR = '_'
NON_ANSWER_CHARS = [BLOCK_CHAR, OPEN_CHAR]  # UNKNOWN_CHAR is a wildcard answer character
EOL = '\n'
SECTION_SEP = EOL + EOL
HEADER_ORDER = ['title', 'author', 'editor', 'copyright', 'date',
                'relation', 'special', 'rebus', 'cluegroup', 'description', 'notes']

unknownpubs = {}
all_files = {}
all_hashes = {}


def clean_str(s):
    cleanchars = string.ascii_letters + string.digits + "-_"
    return "".join(c for c in s if c in cleanchars)


def clean_headers(xd):
    for hdr in xd.headers.keys():
        if hdr in ["Source", "Identifier", "Acquired", "Issued", "Category"]:
            xd.set_header(hdr, None)
        else:
            if hdr.lower() not in HEADER_ORDER:
                log("%s: '%s' header not known: '%s'" % (xd.filename, hdr, xd.headers[hdr]))

    title = xd.get_header("Title") or ""
    author = xd.get_header("Author") or ""
    editor = xd.get_header("Editor") or ""
    rights = xd.get_header("Copyright") or ""

    if author:
        r = r'(?i)(?:(?:By )*(.+)(?:[;/,-]|and) *)?(?:edited|Editor|(?<!\w)Ed[.])(?: By)*(.*)'
        m = re.search(r, author)
        if m:
            author, editor = m.groups()

        if author:
            while author.lower().startswith("by "):
                author = author[3:]

            while author[-1] in ",.":
                author = author[:-1]
        else:
            author = ""

        if " / " in author:
            if not editor:
                author, editor = author.rsplit(" / ", 1)

    if editor:
        while editor.lower().startswith("by "):
            editor = editor[3:]

        while editor[-1] in ",.":
            editor = editor[:-1]

    author = author.strip()
    editor = editor.strip()

    if title.endswith(']'):
        title = title[:title.rfind('[')]

    # title is only between the double-quotes for some USAToday
    if title.startswith("USA Today"):
        if title and title[-1] == '"':
            newtitle = title[title.index('"') + 1:-1]
            if newtitle[-1] == ",":
                newtitle = newtitle[:-1]
        elif title and title[0] == '"':
            newtitle = title[1:title.rindex('"')]
        else:
            newtitle = title

        xd.set_header("Title", newtitle)

#    rights = rights.replace(u"©", "(c)")

    xd.set_header("Author", author)
    xd.set_header("Editor", editor)
    xd.set_header("Copyright", rights)

    if not xd.get_header("Date"):
        abbrid, d = parse_date_from_filename(xd.filename)
        if d:
            xd.set_header("Date", d.strftime("%Y-%m-%d"))


class xdfile:
    def __init__(self, xd_contents=None, filename=None):
        self.filename = filename
        self.source = ""
        self.headers = {}  # [key] -> value or list of values
        self.grid = []  # list of string rows
        self.clues = []  # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""
        self.orig_contents = xd_contents

        if xd_contents:
            self.parse_xd(xd_contents.decode("utf-8"))

    def __str__(self):
        return self.filename or self.source or ""

    def width(self):
        return self.grid and len(self.grid[0]) or 0

    def height(self):
        return len(self.grid)

    # returns (w, h)
    def size(self):
        return (self.width(), self.height())

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
        assert v is None or isinstance(v, basestring), v
        return (v or "").strip()

    def set_header(self, fieldname, newvalue=None):
        newvalue = unicode(newvalue).strip()
        newvalue = " ".join(newvalue.splitlines())
        newvalue = newvalue.replace("\t", "  ")

#        if fieldname in self.headers:
#            if newvalue != self.headers.get(fieldname, None):
#                log("%s[%s] '%s' -> '%s'" % (self.filename, fieldname, self.headers[fieldname], newvalue))

        if newvalue:
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
            return "[XXX]"

        assert len(clues) == 1, Exception("multiple clues for %s: %s" % (target, " | ".join(clues)))
        return clues[0]

    def get_clue(self, clueid):
        for pos, clue, answer in self.clues:
            posdir, n = pos
            if clueid == posdir + str(n):
                return clue

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
                    subsection += 1
                    nblanklines = 0

            if section == 1:
                # headers first
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()

                    if k in self.headers:
                        if isinstance(self.headers[k], basestring):
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

                if pos[0] in string.uppercase:
                    cluedir = pos[0]
                    cluenum = int(pos[1:])
                else:
                    cluedir = ""
                    cluenum = int(pos)

                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else:  # anything remaining
                if line:
                    self.notes += line + EOL

    def to_unicode(self, emit_clues=True):
        # headers (section 1)

        r = u""

        def header_sort_key(item):
            if item[0].lower() not in HEADER_ORDER:
                return 1000

            return HEADER_ORDER.index(item[0].lower())

        if self.headers:
            for k, v in sorted(self.headers.items(), key=header_sort_key):
                assert isinstance(v, basestring), v

                r += "%s: %s" % (k, v)
                r += EOL
        else:
            r += "Title: %s" % utils.parse_pathname(self.source).base
            r += EOL

        r += SECTION_SEP

        # grid (section 2)
        r += EOL.join(self.grid)
        r += EOL + EOL

        # clues (section 3)
        if emit_clues:
            prevdir = None
            for pos, clue, answer in self.clues:
                cluedir, cluenum = pos
                if cluedir != prevdir:
                    r += EOL
                prevdir = cluedir

                r += u"%s%s. %s ~ %s" % (cluedir, cluenum, (clue or "[XXX]").strip(), answer)
                r += EOL

            if self.notes:
                r += EOL + EOL
                r += self.notes

        r += EOL

        # some Postscript CE encodings can be caught here
        r = r.replace(u'\x91', "'")
        r = r.replace(u'\x92', "'")
        r = r.replace(u'\x93', '"')
        r = r.replace(u'\x94', '"')
        r = r.replace(u'\x85', '...')

        # these are always supposed to be double-quotes
        r = r.replace("''", '"')

        return r

    def transpose(self):
        def get_col(g, n):
            return "".join([r[n] for r in g])

        flipxd = xdfile()
        flipxd.filename = self.filename
        flipxd.source = self.source
        flipxd.headers = self.headers.copy()
#        flipxd.set_header("Title", "(transposed) " + flipxd.get_header("Title"))

        g = []
        for i in xrange(len(self.grid[0])):
            g.append(get_col(self.grid, i))

        flipxd.grid = g

        for posdir, posnum, answer in flipxd.iteranswers():
            flipxd.clues.append(((posdir, posnum), self.get_clue_for_answer(answer), answer))

        flipxd.clues = sorted(flipxd.clues)
        return flipxd


def args():
    return g_args

g_corpus = None


def corpus():
    ''' DOCME '''
    global g_corpus
    if g_corpus is not None:
        for xd in g_corpus:
            yield xd

    else:
        g_corpus = []

        global g_args

        parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
        parser.add_argument('-q', '--quiet', dest='verbose', action='store_const', const=-1)
        parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0)
        parser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False, help='abort on exception')
        parser.add_argument('-c', '--corpus', dest='corpusdir', default="crosswords", help='corpus source')
        g_args = parser.parse_args()

        all_files = sorted(utils.find_files(g_args.corpusdir))
        log("%d puzzles" % len(all_files))

        n = 0
        for fullfn, contents in all_files:
            if not fullfn.endswith(".xd"):
                continue

            try:
                basefn = parse_fn(fullfn).base
                n += 1
                progress(n, basefn)

                xd = xdfile(contents, fullfn)

                g_corpus.append(xd)

                yield xd
            except Exception, e:
                log(unicode(e))
                if g_args.debug:
                    raise

        progress(-1)


def load_corpus(*pathnames):
    ret = {}

    n = 0
    for fullfn, contents in utils.find_files(*pathnames):
        if not fullfn.endswith(".xd"):
            continue

        try:
            basefn = parse_fn(fullfn).base
            xd = xdfile(contents, fullfn)

            ret[basefn] = xd

            n += 1
            progress(n, basefn)
        except Exception, e:
            log(unicode(e))
            if g_args.debug:
                raise

    progress()

    return ret


def parse_date_from_filename(fn):
    """
    m = re.search("(\w*)([12]\d{3})-(\d{2})-(\d{2})", fn)
    if m:
        abbr, y, mon, d = m.groups()
        try:
            dt = datetime.date(int(y), int(mon), int(d))
        except:
            dt = None

        return abbr.lower(), dt
    else:
        return parse_fn(fn).base[:3].lower(), None
        """
    abbr, y, mon, d, rest = parse_filename(fn)

    try:
        dt = datetime.date(int(y), int(mon), int(d))
    except:
        dt = None

    return abbr.lower(), dt


def xd_filename(pubid, pubabbr, year, mon, day, unique=""):
    return "crosswords/%s/%s/%s%s-%02d-%02d%s.xd" % (pubid, year, pubabbr, year, mon, day, unique)


def parse_fn(fqpn):
    path, fn = os.path.split(fqpn)
    base, ext = os.path.splitext(fn)
    nt = namedtuple('Pathname', 'path base ext')
    return nt(path=path, base=base, ext=ext)


def get_target_location(xd):
    try:
        try:
            abbr, year, month, day, rest = parse_filename(xd.source.lower())
        except:
            raise UnknownFilenameFormat(xd.source)

        if not xd.get_header("Date"):
            xd.set_header("Date", "%d-%02d-%02d" % (year, month, day))

        if abbr:
            base = "%s%s-%02d-%02d%s" % (abbr, year, month, day, rest)
            outfn = xd_filename(publishers.get(abbr, abbr), abbr, year, month, day)
        else:
            base = "%s-%02d-%02d%s" % (year, month, day, rest)
            outfn = xd_filename("misc", "", year, month, day, rest)
    except UnknownFilenameFormat:
        abbr = ""
        year, month, day = 1980, 1, 1
        outfn = "crosswords/misc/%s.xd" % clean_str(parse_fn(xd.source).base)
    except:
        raise

    return outfn


if __name__ == "__main__":
    main_load()
