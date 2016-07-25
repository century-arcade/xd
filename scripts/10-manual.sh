#!/bin/bash
#
# Usage: <$0> <branch to work on> <zip file to process> <source name>
set -x
set -e

SUMMARYLOG='summary.log'
METADB='meta.db'
WORKDIR='gxd/'

cd $WORKDIR
git checkout master . && git clean -df
#num=$(cat receipts.tsv | grep -v receiptid | wc -l)
num=$(sqlite3 ../${METADB} 'select count(ReceiptId) from receipts')
echo "amount of receipts before run: $num" | tee > ../$SUMMARYLOG

# Checkout and if ok clean tree
git branch -f $1 && git checkout $1 . && git clean -df

cd .. && ./scripts/18-convert2xd.py $2 -o $WORKDIR --extsrc "$3"

#num=$(cat $WORKDIR/receipts.tsv | grep -v receiptid | wc -l)
num=$(sqlite3 ${METADB} 'select count(ReceiptId) from receipts')
echo "amount of receipts after run: $num" | tee > $SUMMARYLOG
