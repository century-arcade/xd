#!/bin/bash
#
# Usage: $0 <config>

source scripts/helpers.sh

XDCONFIG=$1

if [ -n "$XDCONFIG" ]; then
    source $XDCONFIG

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    zone=${REGION}a

    # copy config to shared s3 storage
    $aws s3 cp $XDCONFIG s3://${XDPRIV}/etc/config

    $aws iam create-instance-profile --instance-profile-name xd-scraper
    $aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    # from https://alestic.com/2011/11/ec2-schedule-instance/

    $aws autoscaling create-launch-configuration \
      --launch-configuration-name ${launch_config} \
      --security-groups ${SSH_SECURITY_GID} \
      --iam-instance-profile xd-scraper \
      --key $KEY \
      --instance-type ${INSTANCE_TYPE} \
      --user-data file://scripts/01-ec2-thereafter.sh \
      --image-id ${AMI_ID}

    #instance_id=$($aws ec2 describe-instances --filters "Name=key-name,Values=${KEY}" | jq -r .Reservations[0].Instances[0].InstanceId)
    #echo "Instance ID to modify: ${instance_id}"
    #$aws ec2 modify-instance-attribute --groups ${SSH_SECURITY_GID} --instance-id $instance_id

    $aws autoscaling create-auto-scaling-group \
      --auto-scaling-group "$autoscale_group" \
      --launch-configuration "$launch_config" \
      --availability-zones "$zone" \
      --min-size 0 \
      --max-size 0

    $aws autoscaling suspend-processes \
      --auto-scaling-group "$autoscale_group" \
      --scaling-processes ReplaceUnhealthy

    # UTC at 1am (5pm PST)
   $aws autoscaling put-scheduled-update-group-action \
      --scheduled-action-name "xd-schedule-start" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 1 \
      --max-size 1 \
      --desired-capacity 1 \
      --recurrence "0 01 * * *"

    $aws autoscaling put-scheduled-update-group-action \
      --scheduled-action-name "xd-schedule-stop" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 0 \
      --max-size 0 \
      --desired-capacity 0 \
      --recurrence "55 02 * * *"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
