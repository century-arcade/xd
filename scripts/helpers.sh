
if [ ! -n "$NOW" ]; then
    echo "config not available, run: source config"
    exit 1
fi

if [ -n "$NODRY" ]; then
    aws="aws"
    set -x
else
    aws="echo -e \naws"
fi

sh="bash"
python="/usr/bin/env python3"

# automatically set variables
export S3WWW=s3://${DOMAIN}
export S3PUB=s3://${DOMAIN}/pub
export S3PRIV=s3://${XDPRIV}

