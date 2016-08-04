#!/bin/bash -x
#
# Usage: $0 <config file>
# see format below
#
# export KEY=
# export BRANCH=
# export REGION=
# export AWS_ACCESS_KEY=
# export AWS_SECRET_KEY=
# export BUCKET=
# export EMAIL=
# export XD_GIT=
# export GXD_GIT=
# export XD_PROFILE=

#
#source src/aws/config

aws="aws"
sh="bash"

XDCONFIG=$1
if [ -n "$XDCONFIG" ]; then
    aws s3 cp $XDCONFIG s3://xd-private/etc/config

    ami_id=ami-75fd3b15 #Ubuntu Server 16.04 LTS (HVM)
    ssh_security_gid=sg-e00fbe87
    INSTANCE_JSON=/tmp/instance.json

    #  created via IAM console: role/xd-scraper
    $aws ec2 run-instances \
      --key-name $KEY \
      --region ${REGION} \
      --instance-type r3.large \
      --instance-initiated-shutdown-behavior terminate \
      --iam-instance-profile Arn="$XD_PROFILE" \
      --user-data file://scripts/00-aws-bootstrap.sh \
      --image-id $ami_id > $INSTANCE_JSON

    instance_id=$(cat $INSTANCE_JSON | jq -r .Instances[0].InstanceId)
    $aws ec2 modify-instance-attribute --groups $ssh_security_gid --instance-id $instance_id

    public_ip=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].PublicIpAddress')
    #  Wait till machine will be deployed
    sleep 20 
    ssh -i ~/*.pem ubuntu@$public_ip

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
