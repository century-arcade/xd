#!/bin/bash

WORKDIR=/tmp

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.

export LC_ALL="en_US.UTF-8"
export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log
export SUMLOGFILE=/tmp/`date +"%Y-%m-%d"`summary.log
# To run xdfile based scripts below
export PYTHONPATH=.

exec > >(tee -i ${LOGFILE}) 2>&1
echo 'SUMMARY: Start time:'`date +'%Y-%m-%d %H:%M'`

# Re-get config file from AWS
curl http://169.254.169.254/latest/user-data > $WORKDIR/config
source $WORKDIR/config

HOME=/home/ubuntu

cd $HOME/xd
git pull
git checkout ${BRANCH}

cd $HOME/xd/gxd
ssh-agent bash -c "ssh-add ${HOME}/.ssh/gxd_rsa ; git pull ; git checkout master"

cd $HOME/xd

source scripts/helpers.sh

if [ ! -f $HOME/.ssh/gxd_rsa ] ; then
    mkdir -p $HOME/.ssh
    aws s3 cp --region=$REGION s3://xd-private/etc/gxd_rsa $HOME/.ssh/
    chmod 600 $HOME/.ssh/gxd_rsa
fi

echo "Run deploy script"
/bin/bash scripts/05-full-pipeline.sh

echo 'SUMMARY: End time '`date +'%Y-%m-%d %H:%M'`
# Parse log to get summary to be mailed
egrep -i 'ERROR|WARNING|SUMMARY' ${LOGFILE} > ${SUMLOGFILE}
echo -e '\n' >> ${SUMLOGFILE}

echo "Getting summary"
scripts/48-stats.sh >> ${SUMLOGFILE}
echo -e '\n' >> ${SUMLOGFILE}

echo "SUMMARY: Full log file http://$DOMAIN/logs/`basename ${LOGFILE}`" >> ${SUMLOGFILE}

echo "Sending email"
scripts/send-email.py $ADMIN_EMAIL "execution logs for $TODAY" ${SUMLOGFILE}

echo "Copy logs to AWS"
aws s3 cp --region ${REGION} --content-type='text/plain' ${LOGFILE} s3://${DOMAIN}/logs/ --acl public-read
aws s3 cp --region ${REGION} --content-type='text/plain' ${SUMLOGFILE} s3://${DOMAIN}/logs/ --acl public-read

echo "Make logs index page"
scripts/49b-mkindex.sh
