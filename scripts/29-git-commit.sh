#!/bin/sh

# unshelve into corpus directly

set -e
set -x

TODAY=`date +"%Y%m%d"`
BRANCH=incoming_$TODAY
CORPUSDIR=$1

cd $CORPUSDIR
git checkout -b $BRANCH
git add .
#git commit -m "incoming for $TODAY"
#git push --set-upstream origin $BRANCH

# TODO: submit pull request (setup to add some people automatically on each PR)


