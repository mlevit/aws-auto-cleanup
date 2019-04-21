import boto3
import sys

from lambda_helper import *


class RDSCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('rds', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.instances()
        self.snapshots()
        
    
    def instances(self):
        """
        Deletes RDS Instances. If Instance has termination
        protection enabled, the protection will be first disabled
        and then the Instance will be terminated.
        """
        
        clean = self.settings.get('services').get('rds', {}).get('instances', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_db_instances().get('DBInstances')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('rds', {}).get('instances', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('DBInstanceIdentifier')
                resource_date = resource.get('InstanceCreateTime')

                if resource_id not in self.whitelist.get('rds', {}).get('instance', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            # remove termination prodtection
                            if resource.get('DeletionProtection'):
                                try:
                                    self.client.modify_db_instance(
                                        DBInstanceIdentifier=resource_id,
                                        DeletionProtection=False)
                                    
                                    self.logging.info("RDS Instance '%s' had delete protection turned on and now has been turned off." % (resource_id))
                                except:
                                    self.logging.error("Could not remove termination protection from Instance '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break
                            
                            # delete instance
                            try:
                                self.client.delete_db_instance(
                                    DBInstanceIdentifier=resource_id,
                                    SkipFinalSnapshot=True)
                            except:
                                self.logging.error("Could not delete Instance '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info("RDS Instance '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("RDS Instance '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("RDS Instance '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'RDS', {}).setdefault(
                            'Instances', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of RDS Instances.")
    
    
    def snapshots(self):
        """
        Deletes RDS Snapshots.
        """
        
        clean = self.settings.get('services').get('rds', {}).get('snapshots', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_db_snapshots().get('DBSnapshots')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('rds', {}).get('snapshots', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('DBSnapshotIdentifier')
                resource_date = resource.get('SnapshotCreateTime')

                if resource_id not in self.whitelist.get('rds', {}).get('snapshot', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.delete_db_snapshot(DBSnapshotIdentifier=resource_id)
                            except:
                                self.logging.error("Could not delete Snapshot '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info("RDS Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("RDS Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("RDS Snapshot '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'RDS', {}).setdefault(
                            'Snapshots', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of RDS Snapshots.")