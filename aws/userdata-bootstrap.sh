#!/bin/bash

# This script is passed as userdata to the launch-config, which the base AMI
# executes at the end of initialization.  These configuration parameters
# have to be specified inline here.

export REGION=us-west-2
export BUCKET=xd.example
export BRANCH=master
export EMAIL=xd@example.com

cd /tmp

wget https://raw.githubusercontent.com/century-arcade/xd/${BRANCH}/aws/get-recent-xd.sh

sudo -E /bin/bash -x /tmp/get-recent-xd.sh

sudo poweroff

