#!/usr/bin/env sh
# analyzes all puzzles in gxd/
set -e

mkdir -p $WWW
echo "PUB dir is ${PUB}"
mkdir -p $PUB
rm -f $PUB/*

# regenerate pub/puzzles.tsv
scripts/21-clean-metadata.py $GXD

scripts/25-analyze-puzzle.py -o $WWW/ -c $GXD $GXD
scripts/26-clues-tsv.py -c $GXD -o $PUB/
scripts/27-pubyear-stats.py -c ${GXD}
