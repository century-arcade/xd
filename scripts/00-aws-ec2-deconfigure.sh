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
    autoscale_group=xd-as-group
    launch_config=xd-launch-config

    if [ -n "$NODRY" ]; then
        aws="aws"
    else
        aws="echo -e \naws"
    fi

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

    echo "Wait 10-15 seconds for delete execution"
else
    echo "Supply config file: $0 <config>"
    exit 1
fi
