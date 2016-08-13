#!/bin/bash
#
# Usage: <$0> <branch to work on> <zip file to process> <source name>

BRANCH=$1
INPUT=$2
EXTSRC=$3

set -x
set -e

SUMMARYLOG='summary.log'
METADB='meta.db'
GXD='gxd'
DEBUG=''

cd $GXD
git checkout master && git pull && git clean -df && git reset HEAD . && cd ..

./scripts/05-sql-import-receipts.sh ${METADB}

numtsv=$(cat ${GXD}'/receipts.tsv' | grep -vi CaptureTime | wc -l)
numsql=$(sqlite3 ${METADB} 'select count(*) from receipts')
echo "amount of receipts before run: $numtsv/$numsql tsv/sql" | tee > $SUMMARYLOG

cd $GXD
# Checkout and if ok clean tree
git branch -f $BRANCH && git checkout $BRANCH . && git clean -df
cd ..

./scripts/18-convert2xd.py ${DEBUG} $INPUT -o $GXD/ --extsrc "$EXTSRC"

#num=$(cat $GXD/receipts.tsv | grep -v CaptureTime | wc -l)
num=$(sqlite3 ${METADB} 'select count(*) from receipts')
echo "amount of receipts after run: $num" | tee > $SUMMARYLOG

./scripts/19b-receipts-tsv.sh


