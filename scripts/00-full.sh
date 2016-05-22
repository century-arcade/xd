#!/bin/sh

# Usage:
#  $0 <base>
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

set -e
set -x

#INPUTZIP=$1
#BASE=${INPUTZIP%.*}
#OUTBASEDIR=products/wp${BASE}
#OUTBASE=products/wp${BASE}/${BASE}

TODAY=`date +"%Y%m%d"`
OUTBASEDIR=products/$TODAY
INCOMING_S3PATH=s3://xd.saul.pw/incoming/
OUTBASE=${OUTBASEDIR}/${TODAY}

if [ -d ${OUTBASEDIR} ] ; then
    echo ${OUTBASEDIR} already exists!  remove first.
    exit 1
fi

mkdir -p ${OUTBASEDIR}

mkdir -p ${OUTBASEDIR}/incoming

#aws s3 sync $INCOMING_S3PATH $OUTBASEDIR/incoming/
#scripts/10-parse-email.py -o ${OUTBASE}-email.zip $OUTBASEDIR/incoming
#aws s3 cp ${OUTBASE}-email.zip s3://xd-private/sources/
#aws s3 rm --recursive $INCOMING_S3PATH


#aws s3 cp s3://xd-private/latest.zip $OUTBASEDIR/incoming/
#scripts/10-download-puzzles.py -o ${OUTBASE}-www.zip $OUTBASEDIR/incoming/latest.zip
#aws s3 cp ${OUTBASE}-www.zip s3://xd-private/sources/
#aws s3 cp ${OUTBASE}-www.zip s3://xd-private/latest.zip

scripts/20-convert2xd.py -o ${OUTBASE}-converted.zip ${OUTBASE}-email.zip # ${OUTBASE}-www.zip

scripts/30-shelve.py -o ${OUTBASE}-shelved.zip ${OUTBASE}-converted.zip

#--- groomed to here

scripts/35-git-commit.sh

#scripts/40-catalog-puzzles.py -o ${BASE}/puzzles.tsv ${BASE}
#scripts/50-findsimilar.py -o ${OUTBASE}-similar.tsv ${OUTBASE}-shelved.zip

#scripts/60-mkwww-diffs.py -o www/${BASE} ${OUTBASE}-similar.tsv

#scripts/65-mkwww-publishers -o www/
#scripts/65-mkwww-index.py -o www/${BASE} ${BASE}-similar.tsv

