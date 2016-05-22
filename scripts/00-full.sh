#!/bin/sh

# Usage:
#  $0 <base>
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

set -e
set -x

TODAY=`date +"%Y%m%d"`
NOW=`date +"%Y%m%d-%H%M%S"`
OUTBASEDIR=products/$TODAY
INCOMING_S3PATH=s3://xd-private/incoming/
OUTBASE=${OUTBASEDIR}/${TODAY}

#if [ -d ${OUTBASEDIR} ] ; then
#    echo ${OUTBASEDIR} already exists!  remove first.
#    exit 1
#fi

mkdir -p ${OUTBASEDIR}

# check for email and parse out attachments
mkdir -p ${OUTBASEDIR}/incoming
aws s3 sync $INCOMING_S3PATH $OUTBASEDIR/incoming/
if find "$INCOMING_S3PATH" -mindepth 1 -print -quit | grep -q .; then
    scripts/10-parse-email.py -o ${OUTBASE}-email.zip $OUTBASEDIR/incoming
    aws s3 cp ${OUTBASE}-email.zip s3://xd-private/sources/
    aws s3 rm --recursive $INCOMING_S3PATH
    rm -rf $OUTBASEDIR/incoming
fi

# 1x: download more recent puzzles from www
RECENTS=$OUTBASEDIR/recents.tsv
aws s3 cp s3://xd-private/recent-downloads.tsv $RECENTS
scripts/10-download-puzzles.py -o ${OUTBASE}-www.zip $RECENTS
aws s3 cp ${OUTBASE}-www.zip s3://xd-private/sources/
#unzip ${OUTBASE}-www.zip recents.tsv
aws s3 cp $RECENTS s3://xd-private/recent-downloads.tsv

# 2x: convert everything to .xd, shelve in the proper location, and commit
scripts/20-convert2xd.py -o ${OUTBASE}-converted.zip ${OUTBASE}-email.zip ${OUTBASE}-www.zip

scripts/25-shelve.py -o gxd/ ${OUTBASE}-converted.zip

scripts/29-git-commit.sh gxd

#--- groomed to here

# 3x: statistics and cacheable metadata
# 4x: individual puzzle/grid/clue/answer analyses
# 5x: fun facts (one-off interesting queries)
# 6x: mkwww
# 9x: deploy

#scripts/40-catalog-puzzles.py -o ${BASE}/puzzles.tsv ${BASE}
#scripts/50-findsimilar.py -o ${OUTBASE}-similar.tsv ${OUTBASE}-shelved.zip

#scripts/60-mkwww-diffs.py -o www/${BASE} ${OUTBASE}-similar.tsv

#scripts/65-mkwww-publishers -o www/
#scripts/65-mkwww-index.py -o www/${BASE} ${BASE}-similar.tsv

scripts/95-mkwww-logs.py -o ${OUTBASE}-log.html ${OUTBASEDIR}
aws s3 cp ${OUTBASE}-log.html s3://xd.saul.pw/${NOW}/index.html

scripts/96-cat-logs.py -o log.txt ${OUTBASEDIR}
#aws ses send-email xd@saul.pw log.txt

