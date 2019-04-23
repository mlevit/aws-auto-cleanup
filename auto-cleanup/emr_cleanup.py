import boto3
import sys

from lambda_helper import *


class EMRCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('emr', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.clusters()
        
    
    def clusters(self):
        """
        Deletes EMR Clusters.
        """

        clean = self.settings.get('services').get('emr', {}).get('clusters', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.list_clusters().get('Clusters')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('emr', {}).get('clusters', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('Id')
                resource_date = resource.get('Status').get('Timeline').get('CreationDateTime')
                resource_status = resource.get('Status').get('State')

                if resource_id not in self.whitelist.get('emr', {}).get('clusters', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if resource_status in ('RUNNING', 'WAITING'):
                            if not self.settings.get('general', {}).get('dry_run', True):
                                try:
                                    self.client.terminate_job_flows(
                                        JobFlowIds=[resource_id])
                                except:
                                    self.logging.error("Could not delete EMR Cluster '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break
                            
                            self.logging.info(("EMR Cluster '%s' was created %d days ago "
                                               "and has been deleted.") % (resource_id, delta.days))
                        else:
                            self.logging.debug("EMR Cluster '%s' in state '%s' cannot be deleted." % (resource_id, resource_status))
                    else:
                        self.logging.debug(("EMR Cluster '%s' was created %d days ago "
                                            "(less than TTL setting) and has not been deleted.") % (resource_id, delta.days))
                else:
                    self.logging.debug("EMR Cluster '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'EMR', {}).setdefault(
                            'Clusters', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of EMR Clusters.")