#!/bin/bash -x

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.  These configuration parameters
# have to be specified inline here.

export REGION=us-west-2
export BRANCH=staging_test
export BUCKET=xd-beta.saul.pw
export EMAIL=andjel@gmail.com
export XD_GIT=https://github.com/andjelx/xd.git
export GXD_GIT=git@gitlab.com:rabidrat/gxd.git
export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log

exec > >(tee -i ${LOGFILE}) 2>&1

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes zip awscli python3-lxml python3-pip git markdown && \
    sudo pip3 install cssselect

cd $HOME
echo "Clone main project repo and switch to branch ${BRANCH}"
git clone ${XD_GIT}
cd xd/
git checkout ${BRANCH}

echo "Clone GXD repo"
cp src/aws/id_rsa.pub >> $HOME/.ssh/authorized_keys
cat src/aws/ssh_config >> $HOME/.ssh/config
git clone ${GXD_GIT}

echo "Run deploy script"
/bin/bash -x scripts/00-logging-wrapper.sh

echo "Copy logs"
aws s3 cp --region ${REGION} ${LOGFILE} s3://${BUCKET}/logs/
