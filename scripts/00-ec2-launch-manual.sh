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
      --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"DeleteOnTermination":false}}]' \
      --instance-initiated-shutdown-behavior stop \
      --iam-instance-profile Arn="$XD_PROFILE" \
      --user-data file://scripts/01-sudo-poweroff.sh \
      --image-id ${AMI_ID} > $INSTANCE_JSON

    instance_id=$(cat $INSTANCE_JSON | jq -r .Instances[0].InstanceId)
    echo ${instance_id} started

    echo After it has powered off, run 00-ec2-launch-manual-2.sh ${instance_id}
else
    echo "Supply config file: $0 <config>"
    exit 1
fi

