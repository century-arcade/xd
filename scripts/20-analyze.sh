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

$python scripts/27-pubyear-stats.py -c ${GXD}

$python scripts/26-mkzip-clues.py -c $GXD -o $WWW/xd-clues.zip
$python scripts/28-mkzip-public.py -o $WWW/xd-public.zip $GXD/
$python scripts/29-mkzip-metadata.py -c $GXD -o $WWW/xd-metadata.zip

