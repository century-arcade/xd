#!/bin/sh

# commit all changes to gxd

set -e

BRANCH=incoming_$NOW

cd $GXD
git checkout master
git checkout -b $BRANCH
git add .
git commit -m "incoming for $TODAY"
git push --set-upstream origin $BRANCH

# submit pull request
git request-pull master ${GITURL} $BRANCH
git checkout master


