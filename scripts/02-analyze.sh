#!/usr/bin/env sh

# analyzes all puzzles in gxd/

set -e

BOOTSTRAP_GXD=$GXD.zip

rm -f $PUB/puzzles.tsv
scripts/30-clean-metadata.py -o $PUB/puzzles.tsv $BOOTSTRAP_GXD

# generate pub/pubyears.tsv
scripts/41-pubyears.py -o $PUB

scripts/50-analyze-puzzle.py -o $WWW -c $BOOTSTRAP_GXD $GXD

scripts/51-clues-tsv.py -c $BOOTSTRAP_GXD -o pub

