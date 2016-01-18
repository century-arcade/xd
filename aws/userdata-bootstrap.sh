#!/bin/bash

export REGION=us-west-2
export BUCKET=nantuck.it
export BRANCH=master

cd /tmp

wget https://raw.githubusercontent.com/century-arcade/xd/$(BRANCH)/aws/get-recent-xd.sh

sudo -E /bin/bash -x /tmp/get-recent-xd.sh

sudo poweroff
