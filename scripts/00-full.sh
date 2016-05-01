#!/bin/sh

set -e

BASE=$1
#scripts/10-download-puzzles.py -o ${BASE}-source.zip ${BASE}-prev-source.zip

scripts/20-convert2xd.py -o ${BASE}-converted.zip ${BASE}-source.zip
scripts/25-clean-headers.py -o ${BASE}-cleaned.zip ${BASE}-converted.zip
scripts/30-shelve.py -o ${BASE}-shelved.zip ${BASE}-cleaned.zip
scripts/40-catalog-puzzles.py -o ${BASE}-puzzles.tsv ${BASE}-shelved.zip

