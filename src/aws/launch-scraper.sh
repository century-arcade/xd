#!/bin/bash -x

source src/aws/config

ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

#  created via IAM console: role/xd-scraper
aws ec2 run-instances \
      --key-name $KEY \
      --region ${EC2_REGION} \
      --instance-type t2.medium \
      --instance-initiated-shutdown-behavior terminate \
      --iam-instance-profile Arn="arn:aws:iam::165509303398:instance-profile/xd-scraper" \
      --user-data src/aws/userdata-bootstrap.sh \
      --image-id $ami_id

