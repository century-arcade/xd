#!/bin/bash
#
# Usage: $0 <config file> [NODRY]
# specify NODRY for actual execution
#
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
# export AMI_ID=ami-75fd3b15 #Ubuntu Server 16.04 LTS (HVM)
# export SSH_SECURITY_GID=sg-e00fbe87 # SSH access
# export INSTANCE_TYPE=r3.large
# export QUICKRUN=True # For quickrun scipping 20- and 30- scripts
#

XDCONFIG=$1
NODRY=$2
if [ -n "$XDCONFIG" ]; then
    source $XDCONFIG

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    zone=${REGION}a

    if [ -n "$NODRY" ]; then
        aws="aws"
    else
        aws="echo -e \naws"
    fi

    # copy config on shared s3 storage
    $aws s3 cp $XDCONFIG s3://xd-private/etc/config

    $aws iam create-instance-profile --instance-profile-name xd-scraper
    $aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    # from https://alestic.com/2011/11/ec2-schedule-instance/

    $aws autoscaling create-launch-configuration \
      --launch-configuration-name ${launch_config} \
      --security-groups ${SSH_SECURITY_GID} \
      --iam-instance-profile xd-scraper \
      --key $KEY \
      --instance-type ${INSTANCE_TYPE} \
      --user-data file://scripts/00-aws-bootstrap.sh \
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
      --recurrence "55 01 * * *"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
