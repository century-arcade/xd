#!/bin/bash

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.  These configuration parameters
# have to be specified inline here.

export REGION=us-west-2
export BRANCH=master
export BUCKET=xd.workmuch.com
export EMAIL=xd@workmuch.com

export LOGFILE=/var/log/`date +"%Y-%m-%d"`.log

exec > >(tee ${LOGFILE}|logger -t user-data -s 2>/dev/console) 2>&1

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes zip awscli python-lxml python-pip && \
    sudo pip install cssselect crossword puzpy

cd /tmp

wget https://raw.githubusercontent.com/century-arcade/xd/${BRANCH}/src/aws/get-recent-xd.sh

/bin/bash -x /tmp/get-recent-xd.sh

aws s3 cp --region ${REGION} ${LOGFILE} s3://${BUCKET}/logs/

sudo poweroff

