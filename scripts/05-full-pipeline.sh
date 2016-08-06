#!/bin/bash
#
#

if [ ! -n "$NOW" ]; then
    echo "Seems config-vars were not imported yet"
    source scripts/config-vars.sh
fi

OUTBASEDIR=/tmp/$NOW

# start from a clean $OUTBASEDIR
if [ -d ${OUTBASEDIR} ] ; then
    BACKUPDIR=products/`date +"%Y%m%d-%H%M%S.%N"`
    echo ${OUTBASEDIR} already exists!  moving to $BACKUPDIR
    mv ${OUTBASEDIR} ${BACKUPDIR}
fi

mkdir -p ${OUTBASEDIR}

echo 'Run 10'
/bin/bash scripts/10-import.sh

# Define QUICKRUN to skip time consiming actions
if [ ! -n "$QUICKRUN" ]; then
    echo 'Run 20'
    /bin/bash scripts/20-analyze.sh
    echo 'Run 30'
    /bin/bash scripts/30-mkwww.sh
fi

# commit new puzzles and saved analysis results
/bin/bash scripts/41-git-commit.sh incoming_$TODAY

# capture all logs even if other scripts fail
scripts/39-mkwww-logs.py -o $WWW/$NOW/log.html $TMP

echo 'Run 40'
/bin/bash scripts/40-deploy.sh
