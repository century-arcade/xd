#!/bin/bash
#
# Manage snapshots for EBS storage
# usage: $0 <instance_id>

instance_id=$1

instance_status=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].State')
volume_id=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId')

echo "Instance status"
echo "${instance_status}"

# Get all snapshots for volume
echo "Snapshots"
aws ec2 describe-snapshots --filter Name=volume-id,Values=${volume_id}
