#!/usr/bin/env python

# import os
import sys
# import itertools

import puz2xd


class xdfile:
    def __init__(self, filename=None):
        self.filename = filename
        self.headers = {}  # [key] -> value or list of values
        self.grid = []  # list of string rows
        self.clues = []  # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""
        self.orig_contents = xd_contents

        if xd_contents:
            self.parse_xd(xd_contents.decode("utf-8"))


def parse_xd(xd_contents, fn):
    xd = xdfile(fn)

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

        if section == 1:  # headers first
            assert ":" in line, line

            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()

            assert k not in xd.headers, k
            xd.headers[k] = v

        elif section == 2:  # grid second
            assert xd.headers, "no headers"
            xd.grid.append(line)

        elif section == 3:  # clues third
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

            xd.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))

        else:  # notes last
            xd.notes += line.strip() + EOL

    return xd


def parse_puz(contents, filename):
    rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

    if not filename.lower().endswith('.puz'):
        return

    puzobj = puz.load(contents)

    puzzle = crossword.from_puz(puzobj)

    grid_dict = dict(zip(string.uppercase, string.uppercase))

    xd = xdfile.xdfile()
    xd.filename = filename

    xd.set_header("Author", puzobj.author)
    xd.set_header("Copyright", puzobj.copyright)
    xd.set_header("Notes", puzobj.notes)
    xd.set_header("Postscript", puzobj.postscript)
    xd.set_header("Preamble", puzobj.preamble)

    xd.set_header("Title", puzobj.title)

    rebus = {}
    r = puzobj.rebus()
    if r.has_rebus():
        print puzobj.extensions
        for pair in puzobj.extensions["RTBL"].split(";"):
            pair = pair.strip()
            if not pair:
                continue
            k, v = pair.split(":")
            rebus[k] = v

        rebustr = " ".join([("%s=%s" % (k, v)) for k, v in sorted(rebus.items())])
        xd.set_header("Rebus", rebustr)

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
                n = r * puzobj.width + c
                reb = puzobj.rebus()
                if reb.has_rebus() and n in reb.get_rebus_squares():
                    c = str(reb.table[n] - 1)
                    rowstr += c
                    cell.solution = rebus[c]
                else:
                    if cell.solution not in grid_dict:
                        # grid_dict[cell.solution] = rebus_shorthands.pop()
                        print " odd character '%s'" % cell.solution
                        rowstr += cell.solution
                    else:
                        rowstr += grid_dict[cell.solution]

        xd.grid.append(rowstr)

    # clues
    answers = {}
    clue_num = 1

    for r, row in enumerate(xd.grid):
        for c, cell in enumerate(row):
                # compute number shown in box
                new_clue = False
                if is_block(puzzle, c - 1, r):  # across clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c + j, r):
                        answer += puzzle[c + j, r].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["A" + str(clue_num)] = answer

                if is_block(puzzle, c, r - 1):  # down clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c, r + j):
                        answer += puzzle[c, r + j].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["D" + str(clue_num)] = answer

                if new_clue:
                    clue_num += 1

    for number, clue in puzzle.clues.across():
        xd.clues.append((("A", number), decode(clue), answers["A" + str(number)]))

    for number, clue in puzzle.clues.down():
        xd.clues.append((("D", number), decode(clue), answers["D" + str(number)]))

    return xd


def find_files(*paths):
    import os
    import stat
    for path in paths:
        if stat.S_ISDIR(os.stat(path).st_mode):
            for thisdir, subdirs, files in os.walk(path):
                for fn in files:
                    if fn[0] == ".":
                        continue
                    for f, c in find_files(os.path.join(thisdir, fn)):
                        yield f, c
        else:
            try:
                import zipfile
                with zipfile.ZipFile(path, 'r') as zf:
                    for zi in zf.infolist():
                        fullfn = zi.filename
                        contents = zf.read(zi)
                        yield fullfn, contents
            except:
                fullfn = path
                contents = file(path).read()
                yield fullfn, contents


def num_equal_cells(a, b):
    ncells = 0
    nblocks = 0

    for r in xrange(len(a.grid)):
        row1 = a.grid[r]
        row2 = b.grid[r]
        for i in xrange(len(row1)):
            c1 = row1[i]
            c2 = row2[i]

            if c1 == c2:
                ncells += 1
                if c1 == '#':
                    nblocks += 1

    return ncells, nblocks


def find_similar_to(needle, haystack, min_pct=0.3):
    nrows = len(needle.grid)
    ncols = len(needle.grid[0])
    ncells = float(nrows * ncols)

    for xd in haystack:
        if nrows != len(xd.grid) or ncols != len(xd.grid[0]):
            continue

        nmatch, nblocks = num_equal_cells(needle, xd)

        pct = (nmatch - nblocks) / (ncells - nblocks)

        if pct >= min_pct:
            yield pct, xd

if __name__ == "__main__":
    corpus = load_corpus("xd-grids-2016.xdz")

    print()
    print("\t".join("input similar pct Copyright Title Author Editor".split()))
    for fn, contents in xdfile.find_files(*sys.argv[1:]):
        needle = puz2xd.parse_puz(contents, fn)
        ndups = 0

        for pct, b in find_similar_to(needle, corpus.values()):
            ndups += 1
            bparts = str(b).split("/")
            bid = "%s/%s" % (bparts[1], bparts[-1])
            print("\t".join(unicode(x) for x in [needle, bid, int(pct * 100), b.get_header("Copyright"), b.get_header("Title"), b.get_header("Author"), b.get_header("Editor"),]).encode("utf-8"))

        if ndups == 0:
            print("\t".join(unicode(x) for x in [needle, "None"]))
