#!/bin/bash
#
# Usage: $0 <config file>

XDCONFIG=$1

source $XDCONFIG

source scripts/helpers.sh

if [ -n "$XDCONFIG" ]; then
    $aws s3 cp $XDCONFIG s3://$XDPRIV/etc/config
    INSTANCE_JSON=/tmp/instance.json

    #  created via IAM console: role/xd-scraper
    $aws ec2 run-instances \
      --associate-public-ip-address \
      --subnet-id ${SUBNET_ID} \
      --security-group-ids ${SECURITY_GROUP_ID} \
      --key-name $KEY \
      --region ${REGION} \
      --instance-type ${INSTANCE_TYPE} \
      --no-ebs-optimized \
      --iam-instance-profile Arn="$XD_PROFILE" \
      --user-data file://${XDCONFIG} \
      --image-id ${AMI_ID} > $INSTANCE_JSON

    instance_id=$(cat $INSTANCE_JSON | jq -r .Instances[0].InstanceId)
    echo ${instance_id} started

    sleep 10
    public_ip=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].PublicIpAddress')
    echo "Connect to ${instance_id} :  ssh -i ~/*.pem ubuntu@$public_ip"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi

