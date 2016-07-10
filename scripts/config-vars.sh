#
export PYTHONPATH=.

# account-specific variables
export ACCOUNTID=441803714406
export DOMAIN=xd-beta.saul.pw
export XDPRIV=xd-private
export REGION=us-west-2
export AWS_DEFAULT_REGION=$REGION

export GITURL=git@gitlab.com:rabidrat/gxd.git

# the address to send puzzles
export UPLOAD_EMAIL=upload@${DOMAIN}

# the address to send logs
export ADMIN_EMAIL=andjel@gmail.com
export ADMIN_NAME="Saul Pwanson"

# local directory structure
export GXD=gxd       # the corpus; input-only except for shelve/git-commit
export PRIV=priv     # original sources and non-distributable caches
export PUB=pub       # public non-web intermediates
export WWW=wwwroot   # public website

# dependent variables (should not need to be set)

export S3WWW=s3://${DOMAIN}
export S3PUB=s3://${DOMAIN}/pub
export S3PRIV=s3://${XDPRIV}

export TODAY=`date +"%Y%m%d"`
export NOW=`date +"%Y%m%d-%H%M%S"`

export TMP=`mktemp -d`
