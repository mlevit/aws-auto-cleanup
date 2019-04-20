import boto3
import os
import sys

from lambda_helper import *


class EC2Cleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        
        try:
            self.client = boto3.client('ec2', region_name=region)
            self.resource = boto3.resource('ec2', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.instances()
        self.volumes()
        self.snapshots()
        self.addresses()
    
    
    def addresses(self):
        """
        Deletes Addresses not allocated to an EC2 Instance.
        """

        clean = self.settings.get('services').get('ec2', {}).get('addresses', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_addresses().get('Addresses')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            for resource in resources:
                resource_id = resource.get('AllocationId')

                if resource_id not in self.whitelist.get('ec2', {}).get('address', []):
                    if resource.get('AssociationId') is None:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.release_address(AllocationId=resource_id)
                            except:
                                self.logging.error("Could not release Address '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info("EC2 Address '%s' is not associated with an EC2 instance and has been released." % (resource.get('PublicIp')))
                    else:
                        self.logging.debug("EC2 Address '%s' is associated with an EC2 instance and has not been deleted." % (resource_id))
                else:
                    self.logging.debug("EC2 Address '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'EC2', {}).setdefault(
                            'Addresses', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of EC2 Addresses.")

    
    def instances(self):
        """
        Stops running Instances and terminates stopped instances.
        If Instance has termination protection enabled, the protection will
        be first disabled and then the Instance will be terminated.
        """

        clean = self.settings.get('services').get('ec2', {}).get('instances', {}).get('clean', False)
        if clean:
            try:
                reservations = self.client.describe_instances().get('Reservations')
            except:
                self.logging.error(str(sys.exc_info()))
                return None

            ttl_days = self.settings.get('services').get('ec2', {}).get('instances', {}).get('ttl', 7)
            
            for reservation in reservations:
                for resource in reservation.get('Instances'):
                    resource_id = resource.get('InstanceId')
                    resource_date = resource.get('LaunchTime')
                    resource_state = resource.get('State').get('Name')
                    
                    if resource_id not in self.whitelist.get('ec2', {}).get('instance', []):
                        delta = LambdaHelper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            if resource_state == 'running':
                                if not self.settings.get('general', {}).get('dry_run', True):
                                    try:
                                        self.client.stop_instances(InstanceIds=[resource_id])
                                    except:
                                        self.logging.error("Could not stop Instance '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        break
                                
                                self.logging.info("EC2 Instance '%s' in a 'running' state was last launched %d days ago and has been stopped." % (resource_id, delta.days))
                            elif resource_state == 'stopped':
                                if not self.settings.get('general', {}).get('dry_run', True):
                                    # disable termination protection before terminating the instance
                                    try:
                                        resource_protection = self.client.describe_instance_attribute(
                                            Attribute='disableApiTermination',
                                            InstanceId=resource_id).get('DisableApiTermination').get('Value')
                                    except:
                                        self.logging.error("Could not get if protection for Instance '%s' is on." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        break
                                    
                                    if resource_protection:
                                        try:
                                            self.client.modify_instance_attribute(
                                                DisableApiTermination={'Value': False},
                                                InstanceId=resource_id)
                                        except:
                                            self.logging.error("Could not remove termination protection from Instance '%s'." % resource_id)
                                            self.logging.error(str(sys.exc_info()))
                                            break
                                    
                                        self.logging.info("EC2 Instance '%s' had termination protection turned on and now has been turned off." % (resource_id))
                                
                                    try:
                                        self.client.terminate_instances(InstanceIds=[resource_id])
                                    except:
                                        self.logging.error("Could not delete Instance '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        break
                                
                                self.logging.info("EC2 Instance '%s' in a 'stopped' state was last launched %d days ago and has been terminated." % (resource_id, delta.days))
                        else:
                            self.logging.debug("EC2 Instance '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("EC2 Instance '%s' has been whitelisted and has not been deleted." % (resource_id))
                    
                    self.resource_tree.get('AWS').setdefault(
                        self.region, {}).setdefault(
                            'EC2', {}).setdefault(
                                'Instances', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of EC2 Instances.")
    
    
    def snapshots(self):
        """
        Deletes Snapshots not attached to EBS volumes.
        """

        clean = self.settings.get('services').get('ec2', {}).get('instances', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_snapshots(OwnerIds=[self.account_id]).get('Snapshots')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('ec2', {}).get('snapshots', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('SnapshotId')
                resource_date = resource.get('StartTime')

                if resource_id not in self.whitelist.get('ec2', {}).get('snapshot', []):
                    snapshots_in_use = []
                    try:
                        images = self.client.describe_images(ExecutableUsers=[self.account_id]).get('Images')
                    except:
                        self.logging.error("Could not retrieve AMIs.")
                        self.logging.error(str(sys.exc_info()))
                        break
                    
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
                        delta = LambdaHelper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days:
                            if not self.settings.get('general', {}).get('dry_run', True):
                                try:
                                    self.client.delete_snapshot(SnapshotId=resource_id)
                                except:
                                    self.logging.error("Could not delete Snapshot '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break
                            
                            self.logging.info("EC2 Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            self.logging.debug("EC2 Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("EC2 Snapshot '%s' is currently used by an AMI and cannot been deleted without deleting the AMI first." % (resource_id))
                else:
                    self.logging.debug("EC2 Snapshot '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'EC2', {}).setdefault(
                            'Snapshots', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of EC2 Snapshots.")
    
    
    def volumes(self):
        """
        Deletes Volumes not attached to an EC2 Instance.
        """

        clean = self.settings.get('services').get('ec2', {}).get('addresses', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_volumes().get('Volumes')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('ec2', {}).get('volumes', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('VolumeId')
                resource_date = resource.get('CreateTime')

                if resource_id not in self.whitelist.get('ec2', {}).get('volume', []):
                    if resource.get('Attachments') is None:
                        delta = LambdaHelper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days:
                            if not self.settings.get('general', {}).get('dry_run', True):
                                try:
                                    self.client.delete_volume(VolumeId=resource_id)
                                except:
                                    self.logging.error("Could not delete Volume '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break
                            
                            self.logging.info("EC2 Volume '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            self.logging.debug("EC2 Volume '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("EC2 Volume '%s' is attached to an EC2 instance and has not been deleted." % (resource_id))
                else:
                    self.logging.debug("EC2 Volume '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'EC2', {}).setdefault(
                            'Volumes', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of EC2 Volumes.")