#!/bin/sh

# Run without parameters from the xd directory.
# 

source scripts/config-vars.sh

mkdir -p ${OUTBASEDIR}
mkdir -p ${OUTWWWDIR}

set -x

# check for email and parse out attachments
mkdir -p ${OUTBASEDIR}/incoming
aws s3 sync ${S3PRIV}/incoming $OUTBASEDIR/incoming/
if find $OUTBASEDIR/incoming -mindepth 1 -print -quit | grep -q .; then
    scripts/10-parse-email.py -o ${OUTBASE}-email.zip $OUTBASEDIR/incoming
    aws s3 cp ${OUTBASE}-email.zip ${S3PRIV}/sources/
    aws s3 rm --recursive ${S3PRIV}/incoming
    rm -rf $OUTBASEDIR/incoming
fi

# 1x: download more recent puzzles from www
RECENTS=${CORPUSDIR}/recent-downloads.tsv
scripts/10-download-puzzles.py -o ${OUTBASE}-www.zip -r $RECENTS
aws s3 cp ${OUTBASE}-www.zip ${S3PRIV}/sources/

# 2x: convert everything to .xd, shelve in the proper location, and commit
scripts/20-convert2xd.py -o ${OUTBASE}-converted.zip ${OUTBASE}-email.zip ${OUTBASE}-www.zip

scripts/25-shelve.py -o gxd/ ${OUTBASE}-converted.zip

scripts/29-git-commit.sh gxd


