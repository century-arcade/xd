
# account-specific variables
export ACCOUNTID=165509303398
export DOMAIN=xd.saul.pw
export PRIVATE_BUCKET=xd-private
export REGION=us-west-2

# the address to send puzzles
export UPLOAD_EMAIL=upload@${DOMAIN}

# the address to send logs
export ADMIN_EMAIL=xd@saul.pw

# dependent variables (should not need to be set)

export S3WWW=s3://${DOMAIN}
export S3PRIV=s3://${PRIVATE_BUCKET}

export TODAY=${TODAY:=`date +"%Y%m%d"`}
export NOW=${NOW:=`date +"%Y%m%d-%H%M%S"`}

export OUTBASEDIR=products/${NOW}
export OUTWWWDIR=products/${NOW}/wwwroot
export OUTBASE=${OUTBASEDIR}/${TODAY}
