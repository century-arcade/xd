#!/bin/bash -x

# Usage: $0 <pubid>
# run from crosswords/..

SRCDIR=`pwd`/src
PUBID=$1

${SRCDIR}/mkmeta.sh ${PUBID}

${SRCDIR}/findsimilar.py crosswords/ crosswords/${PUBID}/ > crosswords/${PUBID}/similar.txt

${SRCDIR}/mkwww.py ${PUBID}

