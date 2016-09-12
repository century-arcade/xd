#!/bin/sh -x
#
# Usage: $0 <config file>

source scripts/helpers.sh

XDCONFIG=$1

if [ -n "$XDCONFIG" ]; then
    aws s3 cp $XDCONFIG s3://$XDPRIV/etc/config
    INSTANCE_JSON=/tmp/instance.json

    #  created via IAM console: role/xd-scraper
    $aws ec2 run-instances \
      --key-name $KEY \
      --region ${REGION} \
      --instance-type ${INSTANCE_TYPE} \
      --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"DeleteOnTermination":false}}]' \
      --instance-initiated-shutdown-behavior stop \
      --iam-instance-profile Arn="$XD_PROFILE" \
      --user-data file://scripts/01-ec2-thereafter.sh \
      --image-id ${AMI_ID} > $INSTANCE_JSON

    # Wait a little before applying security group
    sleep 30
    instance_id=$(cat $INSTANCE_JSON | jq -r .Instances[0].InstanceId)
    $aws ec2 modify-instance-attribute --groups ${SSH_SECURITY_GID} --instance-id $instance_id

    # Manual root volume replacement should be done
    current_vol_id=current_vol_id
    VOLUME_ID=VOLUME_ID
    $aws ec2 detach-volume --volume-id $current_volume_id
    $aws ec2 attach-volume --volume-id $VOLUME_ID --instance-id $instance_id --device /dev/sda1
    $aws ec2 delete-volume --volume-id $current_volume_id

    public_ip=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].PublicIpAddress')
    echo "Connect to ${instance_id} :  ssh -i ~/*.pem ubuntu@$public_ip"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi

