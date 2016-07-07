#!/bin/bash -x

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.  These configuration parameters
# have to be specified inline here.

export REGION=us-west-2
export BRANCH=staging
export BUCKET=xd-beta.saul.pw
export EMAIL=andjel@gmail.com
export GXD_GIT=git@gitlab.com:rabidrat/gxd.git
export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log

exec > >(tee -i ${LOGFILE}) 2>&1

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes zip awscli python3-lxml python3-pip git && \
    sudo pip3 install cssselect

cd /tmp

git clone https://github.com/century-arcade/xd

cd xd/
git checkout ${BRANCH}

git clone ${GXD_GIT}

/bin/bash -x scripts/00-logging-wrapper.sh

aws s3 cp --region ${REGION} ${LOGFILE} s3://${BUCKET}/logs/

#sudo poweroff
