#!/usr/bin/python

import sys
import os
import os.path
import stat
import string
import zipfile

flDebug = True # exceptions exit with stack trace

BLOCK_CHAR = '#'
EOL = '\n'

class xdfile:
    def __init__(self, xd_contents=None, filename=None):
        self.filename = filename
        self.headers = [ ]
        self.grid = [ ]
        self.clues = [ ] # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""
        self.orig_contents = xd_contents

        if xd_contents:
            self.parse_xd(xd_contents.decode("utf-8"))

    def get_header(self, fieldname):
        vals = [ v for k, v in self.headers if k == fieldname ]
        if vals:
            assert len(vals) == 1, vals
            return vals[0]

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

                if pos[0] in string.uppercase:
                    cluedir = pos[0]
                    cluenum = pos[1:]
                else:
                    cluedir = ""
                    cluenum = pos

                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else: # anything remaining
                if line:
                    self.notes += line + EOL

    def to_unicode(self):
        # headers (section 1)

        r = u"" 
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
        r = r.replace(u'\x92', "'")
        r = r.replace(u'\x93', '"')
        r = r.replace(u'\x94', '"')
        r = r.replace(u'\x85', '...')

        # these are always supposed to be double-quotes
        r = r.replace("''", '"')

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
                    fullfn = f.filename
                    contents = zf.read(f)
                    yield fullfn, contents
        else:
            fullfn = path
            contents = file(path).read()
            yield fullfn, contents
    
corpus = { }


def load_corpus(*pathnames):
    for fullfn, contents in find_files(*pathnames):
        if not fullfn.endswith(".xd"):
            continue

        try:
            xd = xdfile(contents, fullfn)

            corpus[fullfn] = xd
        except Exception, e:
            x = unicode(e)
            print fullfn, x
            if flDebug:
                raise

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

    parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
    parser.add_argument('path', type=str, nargs='+', help='files, .zip, or directories to be converted')
    parser.add_argument('-o', dest='output', default=None, help='output directory (default stdout)')
    parser.add_argument('-t', dest='toplevel', default=None, help='set toplevel directory of files in .zip')

    args = parser.parse_args()

    outf = sys.stdout

    if args.output:
        outbase, outext = os.path.splitext(args.output)
        if outext == ".zip":
            outf = zipfile.ZipFile(args.output, 'w')
        else:
            outf = None

    for fullfn, contents in find_files(*args.path):
        print "\r" + fullfn,
        try:
            xd = parserfunc(contents)
            xdstr = xd.to_unicode().encode("utf-8")
        except Exception, e:
            if flDebug:
                raise
            else:
                print str(e)
                continue
            
        if isinstance(outf, zipfile.ZipFile):
            if args.toplevel:
                path, fn = os.path.split(fullfn)
                base, ext = os.path.splitext(fn)
                fullfn = "%s/%s/%s.xd" % (args.toplevel, "/".join(path.split("/")[1:]), base)
            else:
                base, ext = os.path.splitext(fullfn)
                fullfn = base + ".xd"

            zi = zipfile.ZipInfo(fullfn)
            zi.external_attr = 0444 << 16L
            zi.compress_type = zipfile.ZIP_DEFLATED
            outf.writestr(zi, xdstr)
        elif isinstance(outf, file):
            outf.write(xdstr)
        else:
            _, fn = os.path.split(fullfn)
            base, ext = os.path.splitext(fn)
            xdfn = "%s/%s.xd" % (args.output, base)
            file(xdfn, "w-").write(xdstr)

    print

if __name__ == "__main__":
    main_load()

