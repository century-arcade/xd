#!/bin/sh

# Usage:
#  $0 <base>
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

set -e

INPUTZIP=$1
BASE=${INPUTZIP%.*}

OUTBASE=products/wp${BASE}/${BASE}

rm -rf products/wp${BASE}
mkdir -p products/wp${BASE}

#scripts/10-download-puzzles.py -o xd-`date +"%Y%m%d"`.zip ${BASE}-latest.zip

scripts/20-convert2xd.py -o ${OUTBASE}-converted.zip ${INPUTZIP}

# clean and shelve into a work product archive
scripts/30-shelve.py -o ${OUTBASE}-shelved.zip ${OUTBASE}-converted.zip

# and also shelve into corpus directly
scripts/30-shelve.py -o crosswords ${OUTBASE}-converted.zip

#scripts/40-catalog-puzzles.py -o ${BASE}/puzzles.tsv ${BASE}
scripts/50-findsimilar.py -o ${OUTBASE}-similar.tsv ${OUTBASE}-shelved.zip

scripts/60-mkwww-diffs.py -o www/${BASE} ${OUTBASE}-similar.tsv
#scripts/65-mkwww-publishers -o www/publishers/ ${BASE}-similar.tsv
#scripts/65-mkwww-index.py -o www/${BASE} ${BASE}-similar.tsv

