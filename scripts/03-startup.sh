#!/bin/bash

export SUMLOGFILE=/tmp/`date +"%Y-%m-%d"`-summary.log

cd $HOME/xd/gxd
ssh-agent bash -c "ssh-add ${HOME}/.ssh/id_rsa ; git pull ; git checkout master"

cd $HOME/xd
git pull; git checkout master

source scripts/helpers.sh

if [ ! -f $HOME/.ssh/id_rsa ] ; then
    mkdir -p $HOME/.ssh
    aws s3 cp --region=$REGION s3://xd-private/etc/id_rsa $HOME/.ssh/
    chmod 600 $HOME/.ssh/id_rsa
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
