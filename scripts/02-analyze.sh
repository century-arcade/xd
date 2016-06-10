#!/usr/bin/env sh

# analyzes all puzzles in gxd/

set -e

BOOTSTRAP_GXD=$GXD.zip

# regenerate pub/puzzles.tsv
rm -f $PUB/puzzles.tsv
scripts/30-clean-metadata.py -o $PUB/puzzles.tsv $GXD $BOOTSTRAP_GXD

# regenerate pub/pubyears.tsv
rm -f $PUB/pubyears.tsv
scripts/41-pubyears.py

scripts/50-analyze-puzzle.py -o $WWW -c $BOOTSTRAP_GXD $GXD

scripts/51-clues-tsv.py -c $GXD -o pub

