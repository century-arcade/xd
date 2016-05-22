#!/bin/bash

aws="echo aws"

XDWWW=xd.saul.pw
XDPRIV=xd-private

$aws s3api create-bucket --bucket $XDWWW
$aws s3api create-bucket --bucket $XDPRIV
