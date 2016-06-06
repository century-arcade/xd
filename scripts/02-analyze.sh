#!/usr/bin/env sh

rm -f $PUB/puzzles.tsv
scripts/30-clean-metadata.py -o $PUB/puzzles.tsv $GXD.zip

# generate pub/pubyears.tsv
scripts/41-pubyears.py -o $PUB

scripts/50-analyze-puzzle.py -o $WWW -c $GXD.zip crosswords/

#scripts/51-clues-tsv.py ${CORPUS} -o pub

