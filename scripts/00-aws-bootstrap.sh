#!/bin/bash

set -x

if [ -z "$HOME" ] ; then
    HOME=/tmp
    export SSHHOME=$HOME
    # Hack for AWS where HOME not set
    if [[ $UID -eq '0' ]]; then
        export SSHHOME=/root
    fi
fi

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.

export LC_ALL="en_US.UTF-8"
export LOGFILE=/tmp/`date +"%Y-%m-%d"`.log
export SUMLOGFILE=/tmp/`date +"%Y-%m-%d"`summary.log
# To run xdfile based scripts below
export PYTHONPATH=.

exec > >(tee -i ${LOGFILE}) 2>&1
echo 'SUMMARY: Start time:'`date +'%Y-%m-%d %H:%M'`

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes language-pack-en-base zip awscli python3-lxml python3-pip git markdown python3-boto3 sqlite3 && \
    sudo pip3 install cssselect botocore

cd $HOME
# Get config file from AWS
aws s3 cp --region=us-west-2 s3://xd-private/etc/config $HOME/config
source $HOME/config

echo "Clone main project repo and switch to branch ${BRANCH}"
git clone ${XD_GIT}
cd xd/
git checkout ${BRANCH}
# Export all config vars
source scripts/config-vars.sh

mkdir -p $SSHHOME/.ssh
echo "Clone GXD repo"
aws s3 cp --region=us-west-2 s3://xd-private/etc/gxd_rsa $SSHHOME/.ssh/
chmod 600 $SSHHOME/.ssh/gxd_rsa

cat src/aws/ssh_config >> $SSHHOME/.ssh/config
ssh-agent bash -c "ssh-add $SSHHOME/.ssh/gxd_rsa; git clone ${GXD_GIT}"

echo "Import all .tsv to sql"
scripts/05-sql-import-receipts.sh

echo "Run deploy script"
/bin/bash scripts/05-full-pipeline.sh

echo 'SUMMARY: End time '`date +'%Y-%m-%d %H:%M'`
# Parse log to get summary to be mailed
egrep -i 'ERROR|WARNING|SUMMARY' ${LOGFILE} > ${SUMLOGFILE}
echo -e '\n' >> ${SUMLOGFILE}

echo "Getting summary"
scripts/48-stats.sh >> ${SUMLOGFILE}
echo -e '\n' >> ${SUMLOGFILE}

echo "SUMMARY: Full log file http://$BUCKET/logs/`basename ${LOGFILE}`" >> ${SUMLOGFILE}

echo "Sending email"
scripts/send-email.py $ADMIN_EMAIL "execution logs for $TODAY" ${SUMLOGFILE}

echo "Copy logs to AWS"
aws s3 cp --region ${REGION} --content-type='text/plain' ${LOGFILE} s3://${BUCKET}/logs/ --acl public-read
aws s3 cp --region ${REGION} --content-type='text/plain' ${SUMLOGFILE} s3://${BUCKET}/logs/ --acl public-read

echo "Make logs index page"
scripts/49b-mkindex.sh
