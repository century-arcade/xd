#!/bin/bash -x
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
    ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    zone=${REGION}a
    #AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

    aws iam create-instance-profile --instance-profile-name xd-scraper
    aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    # from https://alestic.com/2011/11/ec2-schedule-instance/

    as-create-launch-config \
        ${launch_config} \
        ${AUTH} \
      --iam-instance-profile xd-scraper \
      --key $KEY \
      --instance-type t2.medium \
      --user-data-file scripts/00-aws-bootstrap.sh \
      --image-id $ami_id

    as-create-auto-scaling-group \
        ${AUTH} \
      --auto-scaling-group "$autoscale_group" \
      --launch-configuration "$launch_config" \
      --availability-zones "$zone" \
      --min-size 0 \
      --max-size 0

    as-suspend-processes \
        ${AUTH} \
      --auto-scaling-group "$autoscale_group" \
      --processes ReplaceUnhealthy

    # UTC at 1am (5pm PST)
    as-put-scheduled-update-group-action \
        ${AUTH} \
      --name "xd-schedule-start" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 1 \
      --max-size 1 \
      --recurrence "0 01 * * *"

    as-put-scheduled-update-group-action \
        ${AUTH} \
      --name "xd-schedule-stop" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 0 \
      --max-size 0 \
      --recurrence "55 01 * * *"

