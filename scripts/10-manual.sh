#!/bin/bash
#
# Usage: <$0> <branch to work on> <zip file to process> <source name>

source scripts/helpers.sh

BRANCH=$1
INPUT=$2
EXTSRC=$3

set -e

SUMMARYLOG='summary.log'
GXD='gxd'
DEBUG=''

cd $GXD
git checkout -f master && git pull && git clean -df && git reset HEAD . && cd ..

numtsv=$(cat $GXD/receipts.tsv | grep -vi CaptureTime | wc -l)
echo "amount of receipts before run: $numtsv" | tee > $SUMMARYLOG

cd $GXD
# Checkout and if ok clean tree
git branch -f $BRANCH && git checkout $BRANCH . && git clean -df
cd ..

$python scripts/18-convert2xd.py ${DEBUG} $INPUT -o $GXD/ --extsrc "$EXTSRC"

num=$(cat $GXD/receipts.tsv | grep -vi CaptureTime | wc -l)
echo "amount of receipts after run: $num" | tee > $SUMMARYLOG

