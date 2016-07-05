#!/bin/bash

source scripts/config-vars.sh

OUTBASEDIR=/tmp/$NOW

# start from a clean $OUTBASEDIR
if [ -d ${OUTBASEDIR} ] ; then
    BACKUPDIR=products/`date +"%Y%m%d-%H%M%S.%N"`
    echo ${OUTBASEDIR} already exists!  moving to $BACKUPDIR
    mv ${OUTBASEDIR} ${BACKUPDIR}
fi

mkdir -p ${OUTBASEDIR}

export LOGFILE=${OUTBASE}-pipeline.log 

exec > >(tee -i ${LOGFILE}) 2>&1

/bin/bash scripts/10-import.sh
/bin/bash scripts/20-analyze.sh
/bin/bash scripts/30-mkwww.sh

# commit new puzzles and saved analysis results
/bin/bash scripts/41-git-commit.sh incoming_$TODAY

# capture all logs even if other scripts fail
scripts/39-mkwww-logs.py -o $WWW/$NOW/log.html $TMP

/bin/bash scripts/40-deploy.sh

aws s3 cp --region ${REGION} ${LOGFILE} ${S3PRIV}/logs/

src/aws/send-email.py $ADMIN_EMAIL "execution logs for $TODAY" ${LOGFILE}

