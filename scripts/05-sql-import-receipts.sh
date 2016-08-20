#!/bin/bash
#
# Usage: $0 <sqlite file>

METADB=meta.db

if [ ! -f $METADB ] ; then
    sqlite3 $METADB < ./scripts/meta.sql
    ./scripts/tsv2sqlite.py ${DEBUG} --tsvtype "Receipt" -o ${METADB} gxd/receipts.tsv
    ./scripts/tsv2sqlite.py ${DEBUG} --tsvtype "Publication" -o ${METADB} gxd/publications.tsv
    # ./scripts/tsv2sqlite.py ${DEBUG} -o ${METADB} gxd/similar.tsv
else
    echo "$METADB already exists"
fi


