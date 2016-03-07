#!/bin/bash -x

autoscale_group=xd-as-group
launch_config=xd-launch-config

AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

as-delete-scheduled-action \
    ${AUTH} \
  --force \
  --name "xd-schedule-start" \
  --auto-scaling-group "$autoscale_group"

as-delete-scheduled-action \
    ${AUTH} \
  --force \
  --name "xd-schedule-stop" \
  --auto-scaling-group "$autoscale_group"

as-update-auto-scaling-group \
    ${AUTH} \
  --name "$autoscale_group" \
  --min-size 0 \
  --max-size 0

as-delete-auto-scaling-group \
    ${AUTH} \
  --force-delete \
  --auto-scaling-group "$autoscale_group"

as-delete-launch-config \
    ${AUTH} \
  --force \
  --launch-config "$launch_config"

