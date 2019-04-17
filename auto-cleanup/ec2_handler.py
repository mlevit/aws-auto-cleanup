import boto3
import logging
import os
import sys

from helper import *

# enable logging
root = logging.getLogger()

if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.basicConfig(format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)", level=os.environ.get('LOGLEVEL', 'WARNING').upper())


class EC2:
    def __init__(self, helper, whitelist, settings, region):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        
        try:
            self.client = boto3.client('ec2', region_name=region)
            self.resource = boto3.resource('ec2', region_name=region)
        except:
            logging.critical(str(sys.exc_info()))
    
    
    def run(self):
        self.instances()
        self.volumes()
        self.snapshots()
        self.addresses()
    
    
    def instances(self):
        """
        Stops running Instances and terminates stopped instances.
        If Instance has termination protection enabled, the protection will
        be first disabled and then the Instance will be terminated.
        """

        ttl_days = int(self.settings.get('resource', {}).get('ec2_instance_ttl_days', 7))
        try:
            reservations = self.client.describe_instances().get('Reservations')
        except:
            logging.critical(str(sys.exc_info()))
            return None

        for reservation in reservations:
            for resource in reservation.get('Instances'):
                try:
                    resource_id = resource.get('InstanceId')
                    resource_date = resource.get('LaunchTime')
                    resource_state = resource.get('State').get('Name')
                    
                    if resource_id not in self.whitelist.get('ec2', {}).get('instance', []):
                        delta = self.helper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            if resource_state == 'running':
                                if self.dry_run == 'false':
                                    self.client.stop_instances(InstanceIds=[resource_id])
                                
                                logging.info("EC2 Instance '%s' in a 'running' state was last launched %d days ago and has been stopped." % (resource_id, delta.days))
                            elif resource_state == 'stopped':
                                if self.dry_run == 'false':
                                    # disable termination protection before terminating the instance
                                    resource_protection = self.client.describe_instance_attribute(
                                        Attribute='disableApiTermination',
                                        InstanceId=resource_id).get('DisableApiTermination').get('Value')
                                    
                                    if resource_protection:
                                        self.client.modify_instance_attribute(
                                            DisableApiTermination={'Value': False},
                                            InstanceId=resource_id)
                                        
                                        logging.info("EC2 Instance '%s' had termination protection turned on and now has been turned off." % (resource_id))
                                    
                                    self.client.terminate_instances(InstanceIds=[resource_id])
                                    
                                
                                logging.info("EC2 Instance '%s' in a 'stopped' state was last launched %d days ago and has been terminated." % (resource_id, delta.days))
                        else:
                            logging.debug("EC2 Instance '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("EC2 Instance '%s' has been whitelisted and has not been deleted." % (resource_id))
                except:
                    logging.critical(str(sys.exc_info()))
                    return None
                
                return None
    
    
    def volumes(self):
        """
        Deletes Volumes not attached to an EC2 Instance.
        """

        ttl_days = int(self.settings.get('resource', {}).get('ec2_volume_ttl_days', 7))
        try:
            resources = self.client.describe_volumes().get('Volumes')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('VolumeId')
                resource_date = resource.get('CreateTime')

                if resource_id not in self.whitelist.get('ec2', {}).get('volume', []):
                    if resource.get('Attachments') is None:
                        delta = self.helper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days:
                            if self.dry_run == 'false':
                                self.client.delete_volume(VolumeId=resource_id)
                            
                            logging.info("EC2 Volume '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("EC2 Volume '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("EC2 Volume '%s' is attached to an EC2 instance and has not been deleted." % (resource_id))
                else:
                    logging.debug("EC2 Volume '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            return None
    
    
    def snapshots(self):
        """
        Deletes Snapshots not attached to EBS volumes.
        """

        ttl_days = int(self.settings.get('resource', {}).get('ec2_snapshot_ttl_days', 7))
        try:
            resources = self.client.describe_snapshots(OwnerIds=[self.account_id]).get('Snapshots')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('SnapshotId')
                resource_date = resource.get('StartTime')

                if resource_id not in self.whitelist.get('ec2', {}).get('snapshot', []):
                    snapshots_in_use = []
                    images = self.client.describe_images(ExecutableUsers=[self.account_id]).get('Images')
                    
                    for image in images:
                        block_device_mappings = image.get('BlockDeviceMappings')

                        for block_device_mapping in block_device_mappings:
                            if 'Ebs' in block_device_mapping:
                                snapshots_in_use.append(block_device_mapping.get('Ebs').get('SnapshotId'))
                    
                    # cannot retrieve all image to snapshot mappings for whatever reason
                    # to work around this, looking at the Description field of the Snapshot
                    # tells us if the Snapshot was made for an AMI hence prevention its deletion
                    # without first deleting the AMI
                    if resource_id not in snapshots_in_use and 'for ami-' not in resource.get('Description'):
                        delta = self.helper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days: 
                            if self.dry_run == 'false':
                                self.client.delete_snapshot(SnapshotId=resource_id)
                            
                            logging.info("EC2 Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("EC2 Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("EC2 Snapshot '%s' is currently used by an AMI and cannot been deleted without deleting the AMI first." % (resource_id))
                else:
                    logging.debug("EC2 Snapshot '%s' has been whitelisted and has not been deleted." % (resource_id))    
            except:
                logging.critical(str(sys.exc_info()))
            
            return None
    
    
    def addresses(self):
        """
        Deletes Addresses not allocated to an EC2 Instance.
        """

        try:
            resources = self.client.describe_addresses().get('Addresses')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('AllocationId')

                if resource_id not in self.whitelist.get('ec2', {}).get('address', []):
                    if resource.get('AssociationId') is None:
                        if self.dry_run == 'false':
                            self.client.release_address(AllocationId=resource_id)
                        
                        logging.info("EC2 Address '%s' is not associated with an EC2 instance and has been released." % (resource.get('PublicIp')))
                    else:
                        logging.debug("EC2 Address '%s' is associated with an EC2 instance and has not been deleted." % (resource_id))
                else:
                    logging.debug("EC2 Address '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            return None
        