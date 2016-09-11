#!/bin/bash
#
# Usage: $0
# Show stats from meta.db after applying new puzzles

#TOTAL=$(wc -l gxd/receipts.tsv)
#TOTAL_DUP=$(sqlite3 $METADB "select count(*) from (select xdid, count(*) as c from receipts group by xdid having c>=2 order by c);")
#echo "Total/duplicate receipts: $TOTAL/$TOTAL_DUP"
#TOTAL_TSV=$(cat gxd/receipts.tsv | grep -v CaptureTime | wc -l)
#echo "Total in receipts.tsv: $TOTAL_TSV"

#echo "Receipts with empty xdid"
#sqlite3 -header $METADB "select * from receipts where xdid=='';"

