#!/bin/bash
#
# Usage: $0
# Show stats from meta.db after applying new puzzles

METADB='meta.db'

TOTAL=$(sqlite3 $METADB "select count(*) from receipts")
TOTAL_DUP=$(sqlite3 $METADB "select count(*) from (select xdid, count(*) as c from receipts group by xdid having c>=2 order by c);")
echo "Total/duplicate receipts: $TOTAL/$TOTAL_DUP"

echo "Receipts with empty xdid"
sqlite3 -header $METADB "select * from receipts where xdid=='';"

