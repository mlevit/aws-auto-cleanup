import boto3
import logging
import os
import sys

# enable logging
root = logging.getLogger()

if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.basicConfig(format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)", level=os.environ.get('LOGLEVEL', 'WARNING').upper())


class RDS:
    def __init__(self, helper, whitelist, settings, tree, region):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        self.tree = tree
        self.region = region
        
        self.dry_run = settings.get('general', {}).get('dry_run', True)
        
        try:
            self.client = boto3.client('rds', region_name=region)
        except:
            logging.critical(str(sys.exc_info()))
    
    
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
                logging.critical(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('rds', {}).get('instances', {}).get('ttl', 7)
            
            for resource in resources:
                try:
                    resource_id = resource.get('DBInstanceIdentifier')
                    resource_date = resource.get('InstanceCreateTime')

                    if resource_id not in self.whitelist.get('rds', {}).get('instance', []):
                        delta = self.helper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days:
                            if not self.dry_run:
                                if resource.get('DeletionProtection'):
                                    self.client.modify_db_instance(
                                        DBInstanceIdentifier=resource_id,
                                        DeletionProtection=False)
                                    
                                    logging.info("RDS Instance '%s' had delete protection turned on and now has been turned off." % (resource_id))
                                
                                self.client.delete_db_instance(
                                    DBInstanceIdentifier=resource_id,
                                    SkipFinalSnapshot=True)
                            
                            logging.info("RDS Instance '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("RDS Instance '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("RDS Instance '%s' has been whitelisted and has not been deleted." % (resource_id))
                except:
                    logging.critical(str(sys.exc_info()))
                
                self.tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'RDS', {}).setdefault(
                            'Instances', []).append(resource_id)
        else:
            logging.debug("Skipping cleanup of RDS Instances.")
    
    
    def snapshots(self):
        """
        Deletes RDS Snapshots.
        """
        
        clean = self.settings.get('services').get('rds', {}).get('snapshots', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_db_snapshots().get('DBSnapshots')
            except:
                logging.critical(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('rds', {}).get('snapshots', {}).get('ttl', 7)
            
            for resource in resources:
                try:
                    resource_id = resource.get('DBSnapshotIdentifier')
                    resource_date = resource.get('SnapshotCreateTime')

                    if resource_id not in self.whitelist.get('rds', {}).get('snapshot', []):
                        delta = self.helper.get_day_delta(resource_date)
                    
                        if delta.days > ttl_days:
                            if not self.dry_run:
                                self.client.delete_db_snapshot(DBSnapshotIdentifier=resource_id)
                            
                            logging.info("RDS Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("RDS Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("RDS Instance '%s' has been whitelisted and has not been deleted." % (resource_id))
                except:
                    logging.critical(str(sys.exc_info()))
                
                self.tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'RDS', {}).setdefault(
                            'Snapshots', []).append(resource_id)
        else:
            logging.debug("Skipping cleanup of RDS Snapshots.")