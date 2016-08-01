#!/bin/bash
#
# Usage: $0 <sqlite file>

METADB=meta.db

if [ ! -f $METADB ] ; then
    sqlite3 $METADB < ./scripts/meta.sql
    ./scripts/tsv2sqlite.py ${DEBUG} -o ${METADB} gxd/receipts.tsv
fi
