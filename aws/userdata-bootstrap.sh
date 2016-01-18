#!/bin/bash

export KEY=keyname
export REGION=us-west-2
export BUCKET=bucketname

wget http://raw.githubusercontent.com/century-arcade/xd/master/aws/get-recent-xd.sh

exec get-recent-xd.sh

