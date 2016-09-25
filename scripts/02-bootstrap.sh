#!/bin/bash

WORKDIR=/tmp

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.

export LC_ALL="en_US.UTF-8"
export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log
# To run xdfile based scripts below
export PYTHONPATH=.

exec > >(tee -i ${LOGFILE}) 2>&1
echo 'SUMMARY: Start time:'`date +'%Y-%m-%d %H:%M'`

# Re-get config file from AWS
curl http://169.254.169.254/latest/user-data > $WORKDIR/config
source $WORKDIR/config

export HOME=/home/ubuntu

cd $HOME/xd
git pull
git checkout ${BRANCH}

exec scripts/03-startup.sh

