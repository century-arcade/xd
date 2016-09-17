#!/bin/bash

# source /tmp/config
# sudo -E su

apt-get -y autoremove
/bin/rm -f /var/cache/apt/archives/*deb
/bin/rm -rf /mnt/out

mkdir -p /mnt/out

/opt/aws/ec2-ami-tools/bin/ec2-bundle-vol \
 --user ${ACCOUNTID} \
 --privatekey /mnt/xd-pk.pem \
 --cert /mnt/xd-cert.pem \
 --arch x86_64 \
 --destination /mnt/out \
 --partition mbr \
 --include `find / -name "*.pem" | grep -v "^/mnt" | grep -v "^/home" | tr '\n' ','`

ec2-upload-bundle \
--manifest /mnt/out/image.manifest.xml \
--region ${REGION} \
--bucket ${S3AMIDEST} \
--access-key ${AWS_ACCESS_KEY} \
--secret-key ${AWS_SECRET_KEY}

aws ec2 deregister-image --image-id ${AMI_NAME}

echo aws ec2 register-image \
 --image-location ${S3AMIDEST}/image.manifest.xml \
 --region ${REGION} \
 --name ${AMI_NAME} \
 --description '"xd collection and analysis"' \
 --virtualization-type hvm \
 --architecture x86_64

