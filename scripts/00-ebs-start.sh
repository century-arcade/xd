#!/bin/bash
# Start ebs based instance
# Usage: $0 <instance_id>
#

instance_id=$1
aws ec2 start-instances --instance-ids ${instance_id}
sleep 10

instance_status=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].State')

echo ${instance_status}

public_ip=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].PublicIpAddress')

echo "Connect in few seconds: ssh -i ~/*.pem ubuntu@$public_ip"
