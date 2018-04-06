#!/usr/bin/env python3

from xdfile.utils import get_args, open_output, find_files, log, debug, info, error, get_log, COLUMN_SEPARATOR, EOL
from xdfile.utils import parse_tsv, progress, parse_pathname
from xdfileobj import corpus, xdfile, BLOCK_CHAR


# for a given grid
#  for all words,
#    show how many distinct clues there are per publication

# for each pub that has clues for all words,
#    reclue the puzzle with random clues from that pub
#    output the puzzle to .xd


fake_first = "James John Robert Michael William David Richard Charles Joseph Thomas Christopher Daniel Paul Mark Donald George Kenneth Steven Edward Brian Ronald Anthony Kevin Jason Matthew Gary Timothy Jose Mateo Maria Sofia Olivia Linda Barbara Beth Jennifer Susan Margaret Lisa Nancy Karen Betty Helen Sandra Donna Carol Ruth Sharon Michelle Shirley".split()

fake_last = "Smith Johnson Williams Brown Jones Miller Davis Garcia Rodriguez Wilson Martinez Anderson Taylor Thomas Hernandez Moore Martin Jackson Thompson White Lopez Lee Gonzalez Harris Clark Lewis Robinson Walker Perez Hall Young Allen Sanchez Wright King Scott Green Baker Adams Nelson Hill Ramirez Campbell Mitchell Roberts Carter Phillips Evans Turner Torres Parker".split()

import string
import random

# boil a clue down to its letters and numbers only
def boil(s):
    simple = string.ascii_letters + string.digits
    return "".join(c for c in s if c in simple).lower()

# picks a random clue from { 'boiledclue': set(clues) }
def random_clue(s):
    cluepair = random.choice(list(s.items()))
    return random.choice(list(cluepair[1]))

# yields across_word, down_word, i, j  (where across_word[i] and down_word[j] are the pivot characters
def each_word_cross(xd):
    for r, row in enumerate(xd.grid):
        for c, cell in enumerate(row):
            if cell != BLOCK_CHAR:
                # get vert word, find starting pos
                rstart = r
                while xd.cell(rstart-1, c) != BLOCK_CHAR:
                    rstart -= 1
                vwd = ""
                while xd.cell(rstart, c) != BLOCK_CHAR:
                    vwd += xd.cell(rstart, c)
                    rstart += 1

                # get horiz word
                cstart = c
                while xd.cell(r, cstart-1) != BLOCK_CHAR:
                    cstart -= 1

                hwd = ""
                while xd.cell(r, cstart) != BLOCK_CHAR:
                    hwd += xd.cell(r, cstart)
                    cstart += 1

                yield hwd, vwd, c-cstart, r-rstart, r, c


def splice(s, i, repl):
    a, pivot_char, b = s[:i], s[i], s[i:][1:]
    return a + repl + b


def mutate(xd, words, chance=1):
    nmutations = 0
    for hwd, vwd, i, j, r, c in each_word_cross(xd):
        hwd_a, pivot_char, hwd_b = hwd[:i], hwd[i], hwd[i:][1:]
        vwd_a, pivot_char, vwd_b = vwd[:j], vwd[j], vwd[j:][1:]
        progress("%s[%s]%s/%s[%s]%s" % (hwd_a, pivot_char, hwd_b, vwd_a, pivot_char, vwd_b))

        mutations_this_square = []

        for ch in string.ascii_uppercase:
            if ch == pivot_char:
                continue
            new_hwd = hwd_a + ch + hwd_b
            new_vwd = vwd_a + ch + vwd_b

            if new_vwd in words and new_hwd in words:
                mutations_this_square.append((new_hwd, new_vwd, ch))

        if mutations_this_square:
            most_common = sorted(mutations_this_square, key=lambda x: len(words[x[0]]) + len(words[x[1]]))[-1]
            new_hwd, new_vwd, best_replacement = most_common

            if random.random() < chance:
                nmutations += 1
                xd.grid[r] = splice(xd.grid[r], c, best_replacement)
                info("-> %s/%s (%s)" % (new_hwd, new_vwd, "".join(br for h, v, br in mutations_this_square)))
    return nmutations


def load_clues():
    ret = {} # ["pubid"] = { ["ANSWER"] = { ["simplified clue text"] = set(fullclues) } }
    for r in parse_tsv(file("clues.tsv").read(), "AnswerClue"):
        try:
            pubid, dt, answer, clue = r
        except Exception as e:
            print(str(e), r)
            continue

        progress(dt, every=100000)

        if not clue:
            continue

        if "Across" in clue or "Down" in clue:  # skip self-referential clues
            continue

        boiled_clue = boil(clue)
        clue = "%s [%s%s]" % (clue, pubid, dt)

        if pubid not in ret:
            answers = {}
            ret[pubid] = answers
        else:
            answers = ret[pubid]

        if answer not in answers:
            clues = {}
            answers[answer] = clues
        else:
            clues = answers[answer]

        if boiled_clue not in clues:
            clues[boiled_clue] = set()
        clues[boiled_clue].add(clue)

    progress()
    return ret


def reclue(xd, clueset):
    xd.clues = []
    nmissing = 0
    for posdir, posnum, answer in xd.iteranswers():
        if answer not in clueset:
            nmissing += 1
        else:
            clue = random_clue(clueset[answer])
            xd.clues.append(((posdir, posnum), clue, answer))

    xd.clues = sorted(xd.clues)

    return nmissing


def main():
    args = get_args("reclue puzzle with clues from other publications")
    outf = open_output()

    all_clues = load_clues()

    missing_tsv = COLUMN_SEPARATOR.join([ "grid_xdid", "clues_pubid", "num_missing" ]) + EOL

    for fn, contents in find_files(*args.inputs, ext=".xd"):
        xd = xdfile(contents, fn)
        if not xd.grid:
            continue
        xd.set_header("Title", None)
        xd.set_header("Editor", "Timothy Parker Bot")
        xd.set_header("Author", "%s %s" % (random.choice(fake_first), random.choice(fake_last)))
        xd.set_header("Copyright", None)
        xd.set_header("Date", iso8601())

        remixed = set()
        for pubid, pub_clues in list(all_clues.items()):
            try:
                if pubid == xd.publication_id:
                    continue  # don't use same publisher's clues

                nmissing = reclue(xd, pub_clues)

                outfn = "%s-%s.xd" % (xd.xdid(), pubid)

                if nmissing == 0:
                    nmutated = 0
                    while nmutated < 100:
                        nmutated += mutate(xd, pub_clues)
                    nmissing = reclue(xd, pub_clues)
                    info("%s missing %d clues after %d mutations" % (outfn, nmissing, nmutated))

                    remixed.add(pubid)
                    outf.write_file(outfn, xd.to_unicode())
                else:
                    debug("%s missing %d clues" % (outfn, nmissing))

                    missing_tsv += COLUMN_SEPARATOR.join([ xd.xdid(), pubid, str(nmissing) ]) + EOL

            except Exception as e:
                error("remix error %s" % str(e))

        if remixed:
            info("%d remixed: %s" % (len(remixed), " ".join(remixed)))
            try:
                outf.write_file(parse_pathname(fn).base + ".xd", contents.encode("utf-8"))
            except Exception as e:
                error("couldn't write: " + str(e))

    outf.write_file("remix.log", get_log().encode("utf-8"))
    outf.write_file("remix.tsv", missing_tsv)

main()
