#!/bin/sh

# Run without parameters, from the xd directory.
#
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

#source scripts/config-vars.sh

CORPUS="-c $GXD"

mkdir -p wwwroot/pub/gxd


# 
cp $GXD/*.tsv wwwroot/pub/gxd/

# 6x: mkwww

#scripts/60-mkwww-diffs.py -o www/${BASE} pub/similar.tsv

# requires: scripts/41-pubyears.py -o $PUB

## produce an analysis for each puzzle in odd.tsv
#scripts/60-mkwww-odd.py ${CORPUS} -o wwwroot/ $GXD/odd.tsv

scripts/65-mkwww-publishers.py -o $WWW priv/puzzles.tsv

scripts/67-mkwww-clues.py -o $WWW
scripts/68-mkwww-words.py -o $WWW

scripts/70-mkwww-index.py -o $WWW

scripts/71-mkwww-redirects.py -o $WWW $GXD/redirects.tsv

