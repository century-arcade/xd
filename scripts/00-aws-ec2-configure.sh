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


XDCONFIG=$1
NODRY=$2
if [ -n "$XDCONFIG" ]; then
    source $XDCONFIG
    ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    zone=${REGION}a
    #AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

    if [ -n "$NODRY" ]; then
        aws="aws"
    else
        aws="echo -e \naws"
    fi

    $aws iam create-instance-profile --instance-profile-name xd-scraper
    $aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    # from https://alestic.com/2011/11/ec2-schedule-instance/

    $aws autoscaling create-launch-configuration \
      --launch-configuration-name ${launch_config} \
      --iam-instance-profile xd-scraper \
      --key $KEY \
      --instance-type r3.large \
      --user-data file://scripts/00-aws-bootstrap.sh \
      --image-id $ami_id

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
      --recurrence "0 01 * * *"

    $aws autoscaling put-scheduled-update-group-action \
      --scheduled-action-name "xd-schedule-stop" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 0 \
      --max-size 0 \
      --recurrence "55 01 * * *"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
