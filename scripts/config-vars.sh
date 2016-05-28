
# account-specific variables
export ACCOUNTID=165509303398
export DOMAIN=xd.saul.pw
export PRIVATE_BUCKET=xd-private
export REGION=us-west-2

export GITURL=git@gitlab.com:rabidrat/gxd.git

# the address to send puzzles
export UPLOAD_EMAIL=upload@${DOMAIN}

# the address to send logs
export ADMIN_EMAIL=xd@saul.pw

# local directory structure
export GXD=gxd       # the corpus; input-only except for shelve/git-commit
export PRIV=priv     # original sources and non-distributable caches
export PUB=pub       # public non-web intermediates
export WWW=wwwroot   # public website

# dependent variables (should not need to be set)

export S3WWW=s3://${DOMAIN}
export S3PUB=s3://${DOMAIN}/pub
export S3PRIV=s3://${PRIVATE_BUCKET}

export TODAY=`date +"%Y%m%d"`
export NOW=`date +"%Y%m%d-%H%M%S"`

export TMP=`mktemp -d`
