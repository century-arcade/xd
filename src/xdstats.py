#!/usr/bin/python

import xdfile

EOL = '\n'

def get_blank_grid(xd): 
    emptygrid = ""
    for row in xd.grid:
        for c in row:
            if c == BLOCK_CHAR:
                emptygrid += BLOCK_CHAR
            else:
                emptygrid += "."
        emptygrid += EOL
            
    return emptygrid

def find_grid(fn):
    needle = get_blank_grid(xdfile(file(fn).read()))

    return [ xd for xd in corpus.values() if needle == get_blank_grid(xd) ]

def get_all_words():
    ret = { } # ["ANSWER"] = number of uses
    for xd in corpus.values():
        for pos, clue, answer in xd.clues:
            ret[answer] = ret.get(answer, 0) + 1

    return ret

def most_used_grids(n=1):
    import itertools

    all_grids = { }
    for xd in corpus.values():
        empty = get_blank_grid(xd)

        if empty not in all_grids:
            all_grids[empty] = [ ]

        all_grids[empty].append(xd.filename)

    print "%s distinct grids out of %s puzzles" % (len(all_grids), len(corpus))

    most_used = sorted(all_grids.items(), key=lambda x: -len(x[1]))

    for k, v in most_used[0:n]:
        print "used %s times" % len(v)
        gridlines = k.splitlines()
        for g, u in itertools.izip_longest(gridlines, sorted(v)):
            print "%15s    %s" % (u or "", g or "")
        print

def get_duplicate_puzzles():
    dupgrids = { }
    grids = { }
    for xd in corpus.values():
        g = EOL.join(xd.grid)
        if g not in grids:
            grids[g] = [ xd ]
        else:
            grids[g].append(xd)
            dupgrids[g] = grids[g]

    return dupgrids.values()

def load_corpus_zip(pathname):
    ret = { }

    import zipfile
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

def load_corpus(pathname):
    ret = { }
    for thisdir, subdirs, files in os.walk(pathname):
        for fn in files:
            path = os.path.join(thisdir, fn)
            ret[path] = xdfile(file(path).read(), path)
    
    return ret

if __name__ == "__main__":
    import sys

    corpus = xdfile.main()

    print "Duplicates:"
    for xds in get_duplicate_puzzles():
        if len(xds) > 1:
            print " ".join(xd.filename for xd in xds)
    print

    all_words = get_all_words()
    print "%d unique words.  most used words:" % len(all_words)
    for word, num_uses in sorted(all_words.items(), key=lambda x: -x[1])[0:10]:
        print num_uses, word
    print

