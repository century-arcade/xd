#!/bin/bash
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


XDCONFIG=$1
if [ -n "$XDCONFIG" ]; then
    source $XDCONFIG
    # source config
    # ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    #zone=${REGION}a
    #AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

    # one-time setup of xd-scraper
    echo aws iam create-instance-profile --instance-profile-name xd-scraper
    echo aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    aws="echo -e \naws"
    # from https://alestic.com/2011/11/ec2-schedule-instance/
    $aws autoscaling delete-scheduled-action \
        --scheduled-action-name "xd-schedule-start" \
        --auto-scaling-group-name "$autoscale_group"

    $aws autoscaling delete-scheduled-action \
        --scheduled-action-name "xd-schedule-stop" \
        --auto-scaling-group-name "$autoscale_group"

    $aws autoscaling delete-auto-scaling-group \
         --auto-scaling-group "$autoscale_group"

    $aws autoscaling delete-launch-configuration \
        --launch-configuration-name ${launch_config}

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
