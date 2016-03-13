#!/bin/bash -x

# Usage: $0 <pubid>
# run from crosswords/..

WWWDIR=www/xdiffs
SRCDIR=`pwd`/src
PUBID=$1

${SRCDIR}/mkmeta.sh ${PUBID}

${SRCDIR}/findsimilar.py crosswords/ crosswords/${PUBID}/ > crosswords/${PUBID}/similar.txt

${SRCDIR}/mkwww.py ${WWWDIR}/${PUBID}

git add crosswords/${PUBID}/
git commit -m "${PUBID} meta and similar"

mv ${WWWDIR}/${PUBID}/index.txt crosswords/${PUBID}/similar.txt

git add crosswords/${PUBID}/
git commit -m "${PUBID} reduced similar.txt"
