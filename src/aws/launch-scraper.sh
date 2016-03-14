#!/bin/bash -x

ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

#  created via IAM console: role/xd-scraper
ec2-run-instances \
      --key $KEY \
      --region ${EC2_REGION} \
      --instance-type t2.small \
      --instance-initiated-shutdown-behavior terminate \
      --iam-profile xd-scraper \
      --user-data-file src/aws/userdata-bootstrap.sh \
      $ami_id

