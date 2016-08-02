#!/bin/bash
#
# Generates receipts.tsv from sqlite db
#
# Usage: $0

set -x
set -e

METADB='meta.db'
GXD='gxd'
DEBUG=''

./scripts/sqlite2tsv.sh receipts ${GXD}/receipts.tsv
