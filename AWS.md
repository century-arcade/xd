# AWS commands

## Extend root volume of instance
1) Stop instance

2) Create a snapshot
aws ec2 create-snapshot --volume-id {cur_root_volume} --description 'Initial snapshot'

3) Create new root volume; get snapshot id from previous output
aws ec2 create-volume --size {new_size_gb} --region us-west-2 --availability-zone us-west-2a --volume-type standard --snapshot-id {snapshot_id_of_root_volume}

4) Detach existing root volume
aws ec2 detach-volume --volume-id {cur_root_volume}

5) Attach new root volume
aws ec2 attach-volume --volume-id {new_root_volume_step3} --instance-id i-5fc17aca --device /dev/sda1

6) Start instance and process with partition extension
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-expand-volume.html#recognize-expanded-volume-linux

7) If all ok, delete old root volume
ws ec2 delete-volume --volume-id {cur_root_volume_step2}


## Start AWS ESB instance from bootstrap script

cd /tmp
Specify URL to correct GIT repo
wget https://raw.githubusercontent.com/andjelx/xd/staging_ebs/scripts/00-aws-ebs-bootstrap.sh
chmod +x 00-aws-ebs-bootstrap.sh && sudo ./00-aws-ebs-bootstrap.sh

