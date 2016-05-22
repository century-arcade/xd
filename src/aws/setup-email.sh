#!/bin/sh

ACCOUNTID=165509303398
DOMAIN=xd.saul.pw
BUCKET=$DOMAIN
UPLOAD_EMAIL=upload@$DOMAIN
REGION=us-west-2

# Run this script without parameters.  It creates config/ directory and
# populates it with config files.  Modify the configs in this script, and
# commit this script with the production configuration.  usable uppercase
# defaults, like BUCKET.

# In theory, setting aws=aws and running this entire script on a fresh aws
# account should replicate the entire aws functionality, regardless of how many times 
# the configuration has changed.  In practice, some elements may be already set up,
# so cut and paste as needed to complete the configuration.
aws="echo aws"

# configuration directory
config=config

RULESETNAME=RULESETNAME
RULENAME=RULENAME
TOPICNAME=UPLOAD_TOPIC
TOPICARN=arn:aws:sns:$REGION:$ACCOUNTID:$TOPICNAME

mkdir -p $config || exit

## reset everything

$aws ses delete-receipt-rule --rule-set-name $RULESETNAME --rule-name $RULENAME
$aws sns delete-topic --name $TOPICNAME

## one-time manual config

$aws ses verify-domain-identity --domain $BUCKET
# MANUAL: add returned VerificationToken to DNS for domain as TXT

# MANUAL: set MX record to inbound-smtp.us-west-2.amazonaws.com
# WARNING: make sure naked domain $DOMAIN is not a CNAME (which precludes anything else, including MX)

## configuration files
cat <<EOF > $config/create-receipt-rule.json
{
    "RuleSetName": "$RULESETNAME", 
    "Rule": {
        "Name": "$RULENAME", 
        "Enabled": true, 
        "TlsPolicy": "Optional", 
        "Recipients": [
            "$UPLOAD_EMAIL"
        ], 
        "Actions": [
            {
                "S3Action": {
                    "TopicArn": "$TOPICARN", 
                    "BucketName": "$BUCKET", 
                    "ObjectKeyPrefix": "incoming", 
                    "KmsKeyArn": ""
                }
            }
        ], 
        "ScanEnabled": true
    }
}
EOF

cat <<EOF > $config/s3-email-policy.json
{
    "Statement": [
        {
            "Sid": "GiveSESPermissionToWriteEmail",
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "ses.amazonaws.com"
                ]
            },
            "Action": [
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::$BUCKET/*",
            "Condition": {
                "StringEquals": {
                    "aws:Referer": "$ACCOUNTID"
                }
            }
        }
    ]
}
EOF

# these before creating the rule
$aws s3api put-bucket-policy --bucket $BUCKET --policy file://$config/s3-email-policy.json
$aws sns create-topic --name $TOPICNAME



$aws ses create-receipt-rule-set --rule-set-name $RULESETNAME
$aws ses create-receipt-rule --rule-set-name $RULESETNAME --cli-input-json file://$config/create-receipt-rule.json

$aws ses set-active-receipt-rule-set --rule-set-name $RULESETNAME

