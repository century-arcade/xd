#!/bin/bash
#
# Usage: $0 <sqlite file>

sqlite3 $1 < ./scripts/meta.sql

cat << EOF | sqlite3 $1 -echo -init -
.mode tabs
.import gxd/receipts.tsv receipts
