#!/usr/bin/env python

import xdfile

all_clues = { }
corpus = xdfile.main_load()
for xd in corpus.values():
    for pos, clue, answer in xd.clues:
        if answer not in all_clues:
            uses = { }
            all_clues[answer] = uses
        else:
            uses = all_clues[answer]

        if clue not in uses:
            uses[clue] = [ xd ]
        else:
            uses[clue].append(xd)

for answer, uses in sorted(all_clues.items()):
    for clue, xds in sorted(uses.items()):
        try:
            print u",".join([ answer, clue, str(len(xds)) ])
        except:
            print
            print "EXCEPT ", clue.encode("utf-8", 'replace'), map(str, xds)
