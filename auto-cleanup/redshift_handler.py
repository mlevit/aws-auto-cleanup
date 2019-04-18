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

class Redshift:
    def __init__(self, helper, whitelist, settings, tree, region):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        self.tree = tree
        self.region = region
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        try:
            self.client = boto3.client('redshift', region_name=region)
        except:
            logging.critical(str(sys.exc_info()))
    
    
    def run(self):
        self.clusters()
        self.snapshots()
        
    
    def clusters(self):
        """
        Deletes Redshift Clusters.
        """

        ttl_days = int(self.settings.get('resource', {}).get('redshift_clusters_ttl_days', 7))
        try:
            resources = self.client.describe_clusters().get('Clusters')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('ClusterIdentifier')
                resource_date = resource.get('ClusterCreateTime')
                resource_status = resource.get('ClusterStatus')

                if resource_id not in self.whitelist.get('redshift', {}).get('clusters', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if resource_status == 'available':
                            if self.dry_run == 'false':
                                self.client.delete_cluster(
                                    ClusterIdentifier=resource_id, 
                                    SkipFinalClusterSnapshot=True)

                            logging.info("Redshift Cluster '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("Redshift Cluster '%s' in state '%s' cannot be deleted." % (resource_id, resource_status))
                    else:
                        logging.debug("Redshift Cluster '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("Redshift Cluster '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            self.tree.get('AWS').setdefault(
                self.region, {}).setdefault(
                    'Redshift', {}).setdefault(
                        'Clusters', []).append(resource_id)
    
    
    def snapshots(self):
        """
        Deletes Snapshots.
        """

        ttl_days = int(self.settings.get('resource', {}).get('redshift_snapshots_ttl_days', 7))
        try:
            resources = self.client.describe_cluster_snapshots().get('Snapshots')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('SnapshotIdentifier')
                resource_date = resource.get('SnapshotCreateTime')
                resource_status = resource.get('Status')

                if resource_id not in self.whitelist.get('redshift', {}).get('snapshots', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if resource_status in ('available', 'final snapshot'):
                            if self.dry_run == 'false':
                                self.client.delete_cluster_snapshot(SnapshotIdentifier=resource_id)

                            logging.info("Redshift Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            logging.debug("Redshift Snapshot '%s' in state '%s' cannot be deleted." % (resource_id, resource_status))
                    else:
                        logging.debug("Redshift Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("Redshift Snapshot '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            self.tree.get('AWS').setdefault(
                self.region, {}).setdefault(
                    'Redshift', {}).setdefault(
                        'Snapshots', []).append(resource_id)