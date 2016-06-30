#!/bin/bash -x

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.  These configuration parameters
# have to be specified inline here.

export REGION=us-west-2
export BRANCH=master
export BUCKET=xd.saul.pw
export EMAIL=xd@saul.pw

export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log

exec > >(tee -i ${LOGFILE}) 2>&1

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes zip awscli python3-lxml python3-pip git && \
    sudo pip3 install cssselect

cd /tmp

wget https://raw.githubusercontent.com/century-arcade/xd/${BRANCH}/src/aws/get-recent-xd.sh

/bin/bash -x /tmp/get-recent-xd.sh

aws s3 cp --region ${REGION} ${LOGFILE} s3://${BUCKET}/logs/

sudo poweroff

