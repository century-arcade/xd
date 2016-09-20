#!/bin/bash
# analyzes all puzzles in gxd/

source scripts/helpers.sh

set -e

mkdir -p $WWW
echo "PUB dir is ${PUB}"
mkdir -p $PUB
rm -f $PUB/*

# regenerate pub/puzzles.tsv
$python scripts/21-clean-metadata.py $GXD

$python scripts/25-analyze-puzzle.py -o $WWW/ -c $GXD $GXD
$python scripts/26-clues-tsv.py -c $GXD -o $PUB/
$python scripts/27-pubyear-stats.py -c ${GXD}
