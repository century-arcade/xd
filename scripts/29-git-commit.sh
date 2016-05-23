#!/bin/sh

# unshelve into corpus directly

set -e

TODAY=`date +"%Y%m%d"`
NOW=`date +"%Y%m%d-%H%M%S"`

BRANCH=incoming_$NOW
CORPUSDIR=$1
GITURL=git@gitlab.com:rabidrat/gxd.git

cd $CORPUSDIR
git checkout master
git checkout -b $BRANCH
git add .
git commit -m "incoming for $TODAY"
git push --set-upstream origin $BRANCH

# submit pull request
git request-pull master ${GITURL} $BRANCH




