#!/bin/bash
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

$aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name $autoscale_group \
    --min-size 0 \
    --max-size 0 \
    --desired-capacity 0

$aws autoscaling detach-instances \
    --auto-scaling-group-name $autoscale_group \
    --should-decrement-desired-capacity \
    --instance-ids ${INSTANCE_ID} \

$aws autoscaling delete-auto-scaling-group \
     --auto-scaling-group "$autoscale_group"

$aws autoscaling delete-launch-configuration \
    --launch-configuration-name ${launch_config}

echo "Wait 10-15 seconds for delete execution"

