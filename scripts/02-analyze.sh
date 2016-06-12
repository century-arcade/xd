#!/usr/bin/env sh

# analyzes all puzzles in gxd/

set -e

mkdir -p $PUB
rm -f $PUB/*

# regenerate pub/puzzles.tsv
scripts/30-clean-metadata.py -o $PUB/puzzles.tsv $GXD

# regenerate pub/pubyears.tsv
scripts/41-pubyears.py

scripts/50-1-analyze-puzzle.py -o $WWW -c $GXD $GXD

scripts/51-clues-tsv.py -c $GXD -o pub

