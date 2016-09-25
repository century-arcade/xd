#!/bin/bash

source scripts/helpers.sh

set -e

# commit all changes to gxd

git config --global user.email $ADMIN_EMAIL
git config --global user.name $ADMIN_NAME

BRANCH=$1

cd $GXD

if [ -n "$BRANCH" ] ; then
    echo "SUMMARY: Commiting into branch: $BRANCH"
    git checkout master
    git checkout -b $BRANCH || git checkout $BRANCH
    git add .
    git commit -m "incoming for $TODAY"
    ssh-agent bash -c "ssh-add ${HOME}/.ssh/gxd_rsa; git push --set-upstream origin $BRANCH"

    # submit pull request
    git request-pull master ${GXD_GIT} $BRANCH
    git checkout master

#    git merge $BRANCH
#    git branch -d $BRANCH
else
    echo "SUMMARY: Commiting into master"
    git add .
    git commit -m "incoming for $TODAY"
    ssh-agent bash -c "ssh-add ${HOME}/.ssh/gxd_rsa; git push"
fi


