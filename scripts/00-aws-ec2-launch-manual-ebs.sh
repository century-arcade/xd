#!/bin/bash -x
#
# Usage: $0 <config file>
# see format below
#
# export KEY=
# export BRANCH=
# export REGION=
# export AWS_ACCESS_KEY=
# export AWS_SECRET_KEY=
# export BUCKET=
# export EMAIL=
# export XD_GIT=
# export GXD_GIT=
# export XD_PROFILE=
# export AMI_ID=ami-75fd3b15 #Ubuntu Server 16.04 LTS (HVM)
# export SSH_SECURITY_GID=sg-e00fbe87 # SSH access
# export INSTANCE_TYPE=r3.large
# export QUICKRUN=True # For quickrun scipping 20- and 30- scripts
#
#source src/aws/config

aws="aws"
sh="bash"

XDCONFIG=$1
if [ -n "$XDCONFIG" ]; then
    aws s3 cp $XDCONFIG s3://xd-private/etc/config
    source ${XDCONFIG}
    # AMIID - 16.04 LTS amd64   hvm:ebs-ssd
    # https://cloud-images.ubuntu.com/locator/ec2/
    AMI_ID=ami-9ece19fe
    INSTANCE_JSON=/tmp/instance.json

    #  created via IAM console: role/xd-scraper
    $aws ec2 run-instances \
      --key-name $KEY \
      --region ${REGION} \
      --instance-type ${INSTANCE_TYPE} \
      --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"DeleteOnTermination":false}}]' \
      --instance-initiated-shutdown-behavior stop \
      --iam-instance-profile Arn="$XD_PROFILE" \
      --user-data file://scripts/00-aws-bootstrap.sh \
      --image-id ${AMI_ID} > $INSTANCE_JSON

    # Wait a litte before applying sec group
    sleep 30
    instance_id=$(cat $INSTANCE_JSON | jq -r .Instances[0].InstanceId)
    $aws ec2 modify-instance-attribute --groups ${SSH_SECURITY_GID} --instance-id $instance_id

    public_ip=$(aws ec2 describe-instances --instance-ids ${instance_id} | jq -r '.Reservations[0].Instances[0].PublicIpAddress')
    echo "Connecting: ssh -i ~/*.pem ubuntu@$public_ip" 
    ssh -i ~/*.pem ubuntu@$public_ip

else
    echo "Supply config file: $0 <config>"
    exit 1
fi
