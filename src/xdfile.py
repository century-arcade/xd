#!/usr/bin/python

import sys
import os
import os.path
import stat
import string

corpus = None

BLOCK_CHAR = '#'
EOL = '\n'

class xdfile:
    def __init__(self, xd_contents=None, filename=None):
        self.filename = filename
        self.headers = [ ]
        self.grid = [ ]
        self.clues = [ ] # list of (("A", 21), "**Bold**, //italic//, or __underscore__", "MARKUP")
        self.notes = ""

        if xd_contents:
            self.parse_xd(xd_contents)

    def parse_xd(self, xd_contents):
        # placeholders, actual numbering starts at 1
        section = 0
        subsection = 0

        # fake blank line at top to allow leading actual blank lines before headers
        nblanklines = 1

        for line in xd_contents.splitlines():
            # leading whitespace is decorative
            line = line.strip()

            # collapse consecutive lines of whitespace into one line and start next group
            if not line:
                nblanklines += 1
                continue
            else:
                if nblanklines > 0:
                    section += 1
                    subsection = 1
                    nblanklines = 0

            if section == 1:
                # headers first
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()

                    self.headers.append((k, v))
                else:
                    self.headers.append(("", line))  # be permissive
            elif section == 2:
                # grid second
                self.grid.append(line)
            elif section == 3 or section == 4:
                # across or down clues
                answer_idx = line.rfind("~")
                if answer_idx > 0:
                    clue = line[:answer_idx]
                    answer = line[answer_idx+1:]
                else:
                    clue, answer = line, ""

                clue_idx = clue.find(".")

                assert clue_idx > 0, "no clue number: " + clue
                pos = clue[:clue_idx].strip()
                clue = clue[clue_idx+1:]

                if pos[0] in string.digits:
                    cluedir = ""
                    cluenum = int(pos)
                else:
                    cluedir = pos[0]
                    cluenum = int(pos[1:])

                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else: # anything remaining
                self.notes += line + EOL

    def to_unicode(self):
        # headers (section 1)

        r = "" 
        for k, v in self.headers:
            if v:
                r += "%s: %s" % (k or "Header", v)
            r += EOL

        r += EOL + EOL

        # grid (section 2)
        r += EOL.join(self.grid)
        r += EOL + EOL

        # clues (section 3)
        prevdir = None
        for pos, clue, answer in sorted(self.clues):
            cluedir, cluenum = pos
            if cluedir != prevdir:
                r += EOL
            prevdir = cluedir

            r += "%s%s. %s ~ %s" % (cluedir, cluenum, clue, answer)
            r += EOL

        r += EOL + EOL
        r += self.notes
        return r

def find_files(*paths):
    for path in paths:
        if stat.S_ISDIR(os.stat(path).st_mode):
            for thisdir, subdirs, files in os.walk(path):
                for fn in files:
                    if fn[0] == ".":
                        continue
                    for f, c in find_files(os.path.join(thisdir, fn)):
                        yield f, c
        elif path.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(path, 'r') as zf:
                for f in zf.infolist():
                    fullfn = path + ":" + f.filename
                    contents = zf.read(f)
                    yield fullfn, contents
        else:
            fullfn = path
            contents = file(path).read()
            yield fullfn, contents
    
corpus = { }


def load_corpus(*pathnames):
    def collapse_whitespace(s):
        return "".join(x.strip() for x in s.splitlines()).strip()

    for fullfn, contents in find_files(*pathnames):
        if not fullfn.endswith(".xd"):
            continue

        try:
            xd = xdfile(contents, fullfn)

            if collapse_whitespace(xd.to_unicode()) != collapse_whitespace(contents):
                print fullfn, "differs"
#                file(fullfn + ".reparse", 'w').write(xd.to_unicode())

            corpus[fullfn] = xd
        except Exception, e:
            print fullfn, str(e)
#            raise

    return corpus

def main_load():
    global corpus
    corpus = load_corpus(*sys.argv[1:])

    if len(corpus) == 1:
        xd = corpus.values()[0]
        print xd.to_unicode().encode("utf-8")
    else:
        print "%s puzzles" % len(corpus)

    return corpus

def main_parse(parserfunc):
    import os.path
    import sys
    import argparse
    import xdfile

    parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
    parser.add_argument('path', type=str, nargs='+', help='files, .zip, or directories to be converted')
    parser.add_argument('-o', dest='output', default=None,
                   help='output directory (default stdout)')

    args = parser.parse_args()

    for fullfn, contents in xdfile.find_files(*args.path):
        print "\r" + fullfn,
        _, fn = os.path.split(fullfn)
        base, ext = os.path.splitext(fn)
        xd = parserfunc(contents)
        xdstr = xd.to_unicode().encode("utf-8")
        if args.output:
            xdfn = "%s/%s.xd" % (args.output, base)
            file(xdfn, "w-").write(xdstr)
        else:
            print xdstr

    print


if __name__ == "__main__":
    main_load()

