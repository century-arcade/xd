#!/bin/bash

source config

aws iam create-instance-profile --instance-profile-name xd-scraper
aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

#  created via IAM console: role/xd-scraper
ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)
ec2-run-instances \
  --region $REGION \
  --group ssh-only \
  --key $KEY \
  --instance-type t2.nano \
  --instance-initiated-shutdown-behavior terminate \
  --user-data-file aws/userdata-bootstrap.sh \
  --iam-profile xd-scraper \
  $ami_id

