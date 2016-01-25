#!/usr/bin/python

import re

BLOCK_CHAR = '#'
EOL = '\n'

class xdfile:
    def __init__(self, xd_contents, filename=None):
        self.filename = filename
        self.headers = { }
        self.grid = [ ]
        self.clues = [ ]
        self.notes = ""

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
                if clue_idx > 0:
                    pos = clue[:clue_idx]
                    clue = clue[clue_idx+1:]
                else:
                    pos = ""

                self.clues.append((pos.strip(), clue.strip(), answer.strip()))
            else: # anything remaining
                self.notes += line + "\n"

    def __str__(self):
        # headers (section 1)

        r = "" 
        for k, v in self.headers:
            k = k or "Header:"
            if v:
                r += "%s: %s" % (k or "Header", v)
            r += EOL

        r += EOL + EOL

        # grid (section 2)
        r += EOL.join(self.grid)
        r += EOL + EOL

        # clues (section 3)
        prevdir = None
        for pos, clue, answer in sorted(self.clues, key=clue_key):
            if pos[0] != prevdir:
                r += EOL
            prevdir = pos[0]

            r += "%s. %s ~ %s" % (pos, clue, answer)
            r += EOL

        r += EOL + EOL
        r += self.notes
        return r

def clue_key(a):
    m = re.match(r'([A-z]*)(\d+)', a[0])
    if not m:
        raise Exception(str(a))
    section, number = m.groups()
    return (section, int(number))

def load_corpus(fn):
    import zipfile
    ret = { }
    with zipfile.ZipFile(fn) as zf:
        for f in zf.infolist():
            try:
                xd = xdfile(zf.read(f), f.filename)
                assert xd.grid
                ret[f.filename] = xd
            except Exception, e:
                print f.filename
                raise
    
    return ret

def get_blank_grid(xd): 
    empty = [ ]
    for row in self.grid:
        rowstr = ""
        for c in row:
            if c == BLOCK_CHAR:
                rowstr += BLOCK_CHAR
            else:
                rowstr += "."
        empty.append(rowstr)
            
    return "\n".join(empty)

def find_grid(fn):
    needle = get_blank_grid(xdfile(file(fn).read()))

    for xd in haystack.values():
        if needle == get_blank_grid(xd):
            print xd.filename

def get_all_words():
    ret = { } # ["ANSWER"] = number of uses
    for xd in haystack.values():
        for pos, clue, answer in xd.clues:
            ret[answer] = ret.get(answer, 0) + 1

    return ret

def most_used_grids(n=1):
    import itertools

    all_grids = { }
    for xd in haystack.values():
        empty = get_blank_grid(xd)

        if empty not in all_grids:
            all_grids[empty] = [ ]

        all_grids[empty].append(xd.filename)

    print "%s distinct grids out of %s puzzles" % (len(all_grids), len(haystack))

    most_used = sorted(all_grids.items(), key=lambda x: -len(x[1]))

    for k, v in most_used[0:n]:
        print "used %s times" % len(v)
        gridlines = k.splitlines()
        for g, u in itertools.izip_longest(gridlines, sorted(v)):
            print "%15s    %s" % (u or "", g or "")
        print

if __name__ == "__main__":
    import sys

    haystack = load_corpus(sys.argv[1])

    most_used_grids()
    all_words = get_all_words()
    print "%d unique words" % len(all_words)
    for word, num_uses in sorted(all_words.items(), key=lambda x: -x[1])[0:10]:
        print num_uses, word

