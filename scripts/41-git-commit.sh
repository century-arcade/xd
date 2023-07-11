#!/bin/bash

source scripts/helpers.sh

set -e

# commit all changes to gxd

git config --global user.email $ADMIN_EMAIL
git config --global user.name $ADMIN_NAME

cd $GXD

echo "SUMMARY: Commiting into master"
git add .
git commit -m "incoming for $TODAY"
ssh-agent bash -c "ssh-add ${HOME}/.ssh/id_rsa; git push"
