#!/bin/sh
#
# Usage: $0

source scripts/helpers.sh

autoscale_group=xd-as-group
launch_config=xd-launch-config

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
