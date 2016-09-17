#!/bin/bash
#
# Usage: $0 <config>

XDCONFIG=$1

source $XDCONFIG

source scripts/helpers.sh

if [ -n "$XDCONFIG" ]; then

    autoscale_group=xd-as-group
    launch_config=xd-launch-config
    zone=${REGION}a

    $aws iam create-instance-profile --instance-profile-name xd-scraper
    $aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

    # from https://alestic.com/2011/11/ec2-schedule-instance/

    if [ -z "${INSTANCE_ID}" ] ; then
        $aws autoscaling create-launch-configuration \
          --associate-public-ip-address \
          --launch-configuration-name ${launch_config} \
          --security-groups ${SECURITY_GROUP_ID} \
          --key $KEY \
          --instance-type ${INSTANCE_TYPE} \
          --iam-instance-profile xd-scraper \
          --user-data file://${XDCONFIG} \
          --image-id ${AMI_ID}

        INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=key-name,Values=${KEY}" | jq -r .Reservations[0].Instances[0].InstanceId)
    else
        # keep instance running until launch config is created
        $aws ec2 modify-instance-attribute --instance-id ${INSTANCE_ID} --attribute userData --value 'true'

        $aws ec2 start-instances --instance-ids ${INSTANCE_ID}
        #wait until state == "running"
        sleep 10
    fi

    $aws autoscaling create-auto-scaling-group \
      --auto-scaling-group "$autoscale_group" \
      --launch-configuration-name ${launch_config} \
      --availability-zones "$zone" \
      --vpc-zone-identifier ${SUBNET_ID} \
      --min-size 0 \
      --max-size 0

    $aws autoscaling suspend-processes \
      --auto-scaling-group "$autoscale_group" \
      --scaling-processes ReplaceUnhealthy

    # 6am UTC (11pm PST)
   $aws autoscaling put-scheduled-update-group-action \
      --scheduled-action-name "xd-schedule-start" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 1 \
      --max-size 1 \
      --desired-capacity 1 \
      --recurrence "0 ${HOUR_START} * * *"

    $aws autoscaling put-scheduled-update-group-action \
      --scheduled-action-name "xd-schedule-stop" \
      --auto-scaling-group "$autoscale_group" \
      --min-size 0 \
      --max-size 0 \
      --desired-capacity 0 \
      --recurrence "55 ${HOUR_END} * * *"

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
