#!/usr/bin/env sh
# analyzes all puzzles in gxd/
set -e

echo "PUB dir is ${PUB}"
mkdir -p $PUB
rm -f $PUB/*

# regenerate pub/puzzles.tsv
scripts/21-clean-metadata.py -o $PUB/puzzles.tsv $GXD

# regenerate pub/pubyears.tsv
scripts/22-pubyears.py
scripts/25-analyze-puzzle.py -o $WWW -c $GXD $GXD
scripts/26-clues-tsv.py -c $GXD -o pub
