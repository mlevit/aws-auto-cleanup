import boto3
import sys

from lambda_helper import *


class RedshiftCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('redshift', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.clusters()
        self.snapshots()
        
    
    def clusters(self):
        """
        Deletes Redshift Clusters.
        """

        clean = self.settings.get('services').get('redshift', {}).get('clusters', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_clusters().get('Clusters')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('redshift', {}).get('clusters', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('ClusterIdentifier')
                resource_date = resource.get('ClusterCreateTime')
                resource_status = resource.get('ClusterStatus')

                if resource_id not in self.whitelist.get('redshift', {}).get('clusters', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if resource_status == 'available':
                            if not self.settings.get('general', {}).get('dry_run', True):
                                try:
                                    self.client.delete_cluster(
                                        ClusterIdentifier=resource_id,
                                        SkipFinalClusterSnapshot=True)
                                except:
                                    self.logging.error("Could not delete Redshift Cluster '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break

                            self.logging.info("Redshift Cluster '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            self.logging.debug("Redshift Cluster '%s' in state '%s' cannot be deleted." % (resource_id, resource_status))
                    else:
                        self.logging.debug("Redshift Cluster '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("Redshift Cluster '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'Redshift', {}).setdefault(
                            'Clusters', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of Redshift Clusters.")
    
    
    def snapshots(self):
        """
        Deletes Redshift Snapshots.
        """

        clean = self.settings.get('services').get('redshift', {}).get('snapshots', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_cluster_snapshots().get('Snapshots')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('redshift', {}).get('snapshots', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('SnapshotIdentifier')
                resource_date = resource.get('SnapshotCreateTime')
                resource_status = resource.get('Status')

                if resource_id not in self.whitelist.get('redshift', {}).get('snapshots', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if resource_status in ('available', 'final snapshot'):
                            if not self.settings.get('general', {}).get('dry_run', True):
                                try:
                                    self.client.delete_cluster_snapshot(SnapshotIdentifier=resource_id)
                                except:
                                    self.logging.error("Could not delete Redshift Snapshot '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break

                            self.logging.info("Redshift Snapshot '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                        else:
                            self.logging.debug("Redshift Snapshot '%s' in state '%s' cannot be deleted." % (resource_id, resource_status))
                    else:
                        self.logging.debug("Redshift Snapshot '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("Redshift Snapshot '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'Redshift', {}).setdefault(
                            'Snapshots', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of Redshift Snapshots.")