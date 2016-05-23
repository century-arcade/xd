#!/bin/sh

# Usage:
#  $0 <base>
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

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
RECENTS=$OUTBASEDIR/recents.tsv
aws s3 cp ${S3PRIV}/recent-downloads.tsv $RECENTS
scripts/10-download-puzzles.py -o ${OUTBASE}-www.zip $RECENTS
aws s3 cp ${OUTBASE}-www.zip ${S3PRIV}/sources/
unzip ${OUTBASE}-www.zip recents.tsv
aws s3 cp $RECENTS ${S3PRIV}/recent-downloads.tsv

# 2x: convert everything to .xd, shelve in the proper location, and commit
scripts/20-convert2xd.py -o ${OUTBASE}-converted.zip ${OUTBASE}-email.zip ${OUTBASE}-www.zip

scripts/25-shelve.py -o gxd/ ${OUTBASE}-converted.zip

scripts/29-git-commit.sh gxd

#--- groomed to here

# 3x: statistics and cacheable metadata
# 4x: individual puzzle/grid/clue/answer analyses
# 5x: fun facts (one-off interesting queries)
# 6x: mkwww

#scripts/40-catalog-puzzles.py -o ${BASE}/puzzles.tsv ${BASE}
#scripts/50-findsimilar.py -o ${OUTBASE}-similar.tsv ${OUTBASE}-shelved.zip

#scripts/60-mkwww-diffs.py -o www/${BASE} ${OUTBASE}-similar.tsv

#scripts/65-mkwww-publishers -o www/
#scripts/65-mkwww-index.py -o www/${BASE} ${BASE}-similar.tsv

# 9x: deploy

scripts/95-mkwww-logs.py -o ${OUTWWWDIR}/${NOW}/log.html ${OUTBASEDIR}

aws s3 sync ${OUTWWWDIR} ${S3WWW}/ --acl public-read

