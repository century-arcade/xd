#!/bin/bash -x
#
# Usage: $0

aws ec2 describe-security-groups
aws ec2 describe-vpcs
aws ec2 describe-route-tables
aws ec2 describe-internet-gateways
aws ec2 describe-subnets
aws autoscaling describe-auto-scaling-groups
aws autoscaling describe-launch-configurations

