#!/bin/bash
#
# Usage: <$0> <branch to work on> <zip file to process> <external source> [internal source]

source scripts/helpers.sh

BRANCH=$1
INPUT=$2
EXTSRC=$3
INTSRC=$4

set -e

SUMMARYLOG='summary.log'
GXD='gxd'
DEBUG=''

cd $GXD
git checkout -f master && git pull && git clean -df && git reset HEAD . && cd ..

count_receipts() {
	if [ -f $GXD/receipts.jsonl ]; then wc -l < $GXD/receipts.jsonl; else grep -vci CaptureTime $GXD/receipts.tsv; fi
}

numtsv=$(count_receipts)
echo "amount of receipts before run: $numtsv" | tee > $SUMMARYLOG

cd $GXD
# Checkout and if ok clean tree
git branch -f $BRANCH && git checkout $BRANCH . && git clean -df
cd ..

if [ -n "$INTSRC" ]; then
	$python scripts/18-convert2xd.py ${DEBUG} "$INPUT" -o "$GXD/" --extsrc "$EXTSRC" --intsrc "$INTSRC"
else
	$python scripts/18-convert2xd.py ${DEBUG} "$INPUT" -o "$GXD/" --extsrc "$EXTSRC"
fi

num=$(count_receipts)
echo "amount of receipts after run: $num" | tee > $SUMMARYLOG

