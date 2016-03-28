#!/usr/bin/python
# -*- coding: utf-8

import sys
import os
import re
import datetime
# import stat
import string
import zipfile
import argparse

import utils


def log(s):
    sys.stdout.flush()
    sys.stderr.flush()
    print >>sys.stderr, " " + s

BLOCK_CHAR = '#'
EOL = '\n'
SECTION_SEP = EOL + EOL
HEADER_ORDER = ['title', 'author', 'editor', 'copyright', 'date',
                'special', 'rebus', 'cluegroup', 'description']

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

unknownpubs = {}
all_files = {}


def clean_headers(xd):
    for hdr in xd.headers.keys():
        assert hdr in "Title Author Editor Copyright Date Rebus Notes".split(), hdr

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
            assert not editor
            author, editor = author.split(" / ")

    if editor:
        while editor.lower().startswith("by "):
            editor = editor[3:]

        while editor[-1] in ",.":
            editor = editor[:-1]

    author = author.strip()
    editor = editor.strip()

#    rights = rights.replace(u"©", "(c)")

    xd.set_header("Title", title)
    xd.set_header("Author", author)
    xd.set_header("Editor", editor)
    xd.set_header("Copyright", rights)

    # title is only between the double-quotes (some USAToday)
    """
    title = xd.get_header("Title")
    if title and title[-1] == '"':
        newtitle = title[title.index('"')+1:-1]
        if newtitle[-1] == ",":
            newtitle = newtitle[:-1]
    elif title and title[0] == '"':
        newtitle = title[1:title.rindex('"')]
    else:
        newtitle = title

    xd.set_header("Title", newtitle)
    """

    if not xd.get_header("Date"):
        abbrid, d = parse_date_from_filename(xd.filename)
        if d:
            xd.set_header("Date", d.strftime("%Y-%m-%d"))


def parse_date_from_filename(fn):
    m = re.search("(\w*)([12]\d{3})-(\d{2})-(\d{2})", fn)
    if m:
        abbr, y, mon, d = m.groups()
        try:
            dt = datetime.date(int(y), int(mon), int(d))
        except:
            dt = None

        return abbr.lower(), dt
    else:
        return fn[:3].lower(), None


class xdfile:
    def __init__(self, xd_contents=None, filename=None):
        self.filename = filename
        self.headers = {}  # [key] -> value or list of values
        self.grid = []  # list of string rows
        self.clues = []  # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""
        self.orig_contents = xd_contents

        if xd_contents:
            self.parse_xd(xd_contents.decode("utf-8"))

    def __str__(self):
        return self.filename

    def get_header(self, fieldname):
        v = self.headers.get(fieldname)
        assert v is None or isinstance(v, basestring), v
        return (v or "").strip()

    def set_header(self, fieldname, newvalue=None):
        newvalue = unicode(newvalue).strip()

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

    def get_clue(self, clueid):
        for pos, clue, answer in self.clues:
            posdir, n = pos
            if clueid == posdir + str(n):
                return clue

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
                    cluenum = pos[1:]
                else:
                    cluedir = ""
                    cluenum = pos

                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else:  # anything remaining
                if line:
                    self.notes += line + EOL

    def to_unicode(self, emit_clues=True):
        # headers (section 1)

        r = u""
        for k, v in sorted([(x, y) for x, y in self.headers.items()], key=lambda i: i[0].lower() in HEADER_ORDER and HEADER_ORDER.index(i[0].lower() or 1000)):
            if not isinstance(v, list):
                values = [v]
            else:
                values = v

            for i in values:
                r += "%s: %s" % (k, i)
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

                r += u"%s%s. %s ~ %s" % (cluedir, cluenum, clue.strip(), answer)
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


def get_base_filename(fn):
    path, b = os.path.split(fn)
    b, ext = os.path.splitext(b)

    return b

g_corpus = None


def corpus():
    global g_corpus
    if g_corpus is None:
        g_corpus = load_corpus("crosswords")  # "xd-grids-2016.xdz")

    return sorted(g_corpus.values(), key=lambda xd: xd.filename)


def load_corpus(*pathnames):
    ret = {}

    n = 0
    for fullfn, contents in utils.find_files(*pathnames):
        if not fullfn.endswith(".xd"):
            continue

        try:
            basefn = get_base_filename(fullfn)
            n += 1
            if n % 100 == 0:
                print "\r% 6d %s" % (n, basefn),
            xd = xdfile(contents, fullfn)

            ret[basefn] = xd
        except Exception, e:
            print unicode(e)
            # if args.debug:
            #    raise

    print >>sys.stderr, ""

    return ret

SEP = "\t"


def metadata_header():
    return SEP.join([
        "pubid",
        "pubvol",
        "Date",
        "Title",
        "Author",
        "Editor",
    ])


def metadata_line(xd):
    abbrid, d = parse_date_from_filename(xd.filename)
    pubid = xd.filename.split("/")[1]

    fields = [
        pubid,
        abbrid + str(d.year),
        xd.get_header("Date") or d.strftime("%Y-%m-%d"),
        xd.get_header("Title") or "",
        xd.get_header("Author") or "",
        xd.get_header("Editor") or "",
    ]

    assert SEP not in "".join(fields), fields
    return SEP.join(fields).encode("utf-8")


def parse_filename(fn):
    import re
    m = re.search("([A-z]*)[_\s]?(\d{2,4})-?(\d{2})-?(\d{2})(.*)\.", fn)
    if m:
        abbr, yearstr, monstr, daystr, rest = m.groups()
        year, mon, day = int(yearstr), int(monstr), int(daystr)
        if len(yearstr) == 2:
            if year > 1900:
                pass
            elif year > 18:
                year += 1900
            else:
                year += 2000
        assert len(abbr) <= 5, fn
        assert year > 1920 and year < 2017, "bad year %s" % yearstr
        assert mon >= 1 and mon <= 12, "bad month %s" % monstr
        assert day >= 1 and day <= 31, "bad day %s" % daystr
#        print "%s %d-%02d-%02d" % (abbr, year, mon, day)
        return abbr, year, mon, day, "".join(rest.split())[:3]


def xd_filename(pubid, pubabbr, year, mon, day, unique=""):
    return "crosswords/%s/%s/%s%s-%02d-%02d%s.xd" % (pubid, year, pubabbr, year, mon, day, unique)


def main_load():
    corpus = load_corpus(*sys.argv[1:])

    if len(corpus) == 1:
        xd = corpus.values()[0]
        print xd.to_unicode().encode("utf-8")
    else:
        log("%s puzzles" % len(corpus))

    return corpus


def save_file(xd):
    try:
        abbr, year, month, day, rest = parse_filename(xd.filename.lower())
        if not xd.get_header("Date"):
            xd.set_header("Date", "%d-%02d-%02d" % (year, month, day))

        if abbr:
            base = "%s%s-%02d-%02d%s" % (abbr, year, month, day, rest)
            outfn = xd_filename(publishers.get(abbr, abbr), abbr, year, month, day, rest)
        else:
            base = "%s-%02d-%02d%s" % (year, month, day, rest)
    except Exception, e:
        abbr = ""
        year, month, day = 1980, 1, 1
        outfn = "crosswords/misc/%s.xd" % base

    if args.toplevel:
        fullfn = "%s/%s/%s.xd" % (args.toplevel, "/".join(path.split("/")[1:]), base)
    else:
        base, ext = os.path.splitext(fullfn)
        fullfn = base + ".xd"

    xd.filename = fullfn
    clean_headers(xd)

    xdstr = xd.to_unicode().encode("utf-8")

    while outfn in all_files:
        if all_files[outfn] != xdstr:
            log("different versions: '%s'" % outfn)
            outfn += ".2"

    all_files[outfn] = xdstr

    if isinstance(outf, zipfile.ZipFile):
        if year < 1980:
            year = 1980
        zi = zipfile.ZipInfo(outfn, (year, month, day, 9, 0, 0))
        zi.external_attr = 0444 << 16L
        zi.compress_type = zipfile.ZIP_DEFLATED
        outf.writestr(zi, xdstr)
    elif isinstance(outf, file):
        outf.write(xdstr)
    else:
        try:
            basedirs, fn = os.path.split(outfn)
            os.makedirs(basedirs)
        except:
            pass
        file(outfn, "w-").write(xdstr)

def main_parse(parserfunc):

    parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
    parser.add_argument('path', type=str, nargs='+', help='files, .zip, or directories to be converted')
    parser.add_argument('-o', dest='output', default=None, help='output directory (default stdout)')
    parser.add_argument('-t', dest='toplevel', default=None, help='set toplevel directory of files in .zip')
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help='abort on exception')
    parser.add_argument('-m', dest='metadata_only', action='store_true', default=False, help='output metadata.tsv only')

    args = parser.parse_args()

    outf = sys.stdout

    if args.output:
        outbase, outext = os.path.splitext(args.output)
        if outext == ".zip":
            outf = zipfile.ZipFile(args.output, 'w')
        else:
            outf = None

    for fullfn, contents in sorted(utils.find_files(*args.path)):
        print "\r" + fullfn,
        path, fn = os.path.split(fullfn)
        base_orig, ext = os.path.splitext(fn)
        base = "".join([c for c in base_orig.lower()
                        if c in string.lowercase or c in string.digits])
        if base != base_orig:
            print base_orig, base
        try:
            xd = parserfunc(contents, fullfn)

            if not xd:
                print
                continue

            if args.metadata_only:
                print metadata_row(xd)
            else:
                save_file(xd)
        except Exception, e:
            if args.debug:
                raise
            else:
                log("error: %s: %s" % (str(e), type(e)))
                continue

        if abbr and abbr not in publishers:
            rights = xd.get_header("Copyright")
            if rights:
                publishers[abbr] = abbr
                if abbr not in unknownpubs:
                    unknownpubs[abbr] = set()
                unknownpubs[abbr].add(rights.strip())

    for k, v in unknownpubs.items():
        print k, "\n".join(v)

if __name__ == "__main__":
    main_load()
