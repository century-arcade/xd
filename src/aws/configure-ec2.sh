#!/bin/bash -x

# source config
ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

autoscale_group=xd-as-group
launch_config=xd-launch-config
zone=${REGION}a
AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

aws iam create-instance-profile --instance-profile-name xd-scraper
aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

# from https://alestic.com/2011/11/ec2-schedule-instance/

as-create-launch-config \
    ${AUTH} \
  --key $KEY \
  --instance-type t2.nano \
  --user-data-file src/aws/userdata-bootstrap.sh \
  --region ${REGION} \
  --image-id $ami_id \
  --launch-config "$launch_config"

as-create-auto-scaling-group \
    ${AUTH} \
  --auto-scaling-group "$autoscale_group" \
  --launch-configuration "$launch_config" \
  --region ${REGION} \
  --availability-zones "$zone" \
  --min-size 0 \
  --max-size 0

as-suspend-processes \
    ${AUTH} \
  --auto-scaling-group "$autoscale_group" \
  --region ${REGION} \
  --processes ReplaceUnhealthy

# UTC at 1am (5pm PST)
as-put-scheduled-update-group-action \
    ${AUTH} \
  --name "xd-schedule-start" \
  --region ${REGION} \
  --auto-scaling-group "$autoscale_group" \
  --min-size 1 \
  --max-size 1 \
  --recurrence "0 01 * * *"

as-put-scheduled-update-group-action \
    ${AUTH} \
  --region ${REGION} \
  --name "xd-schedule-stop" \
  --auto-scaling-group "$autoscale_group" \
  --min-size 0 \
  --max-size 0 \
  --recurrence "55 01 * * *"

# launch now if any script parameters
if [ -n "$1" ] ; then
    #  created via IAM console: role/xd-scraper
    ec2-run-instances \
      --region $REGION \
      --group ssh-only \
      --key $KEY \
      --instance-type t2.nano \
      --instance-initiated-shutdown-behavior terminate \
      --iam-profile xd-scraper \
      --user-data-file src/aws/userdata-bootstrap.sh \
      $ami_id
fi
