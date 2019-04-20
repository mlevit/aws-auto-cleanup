import boto3
import sys

from lambda_helper import *


class CloudFormationCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('cloudformation', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.stacks()
        
        
    def stacks(self):
        """
        Deletes CloudFormation Stacks.
        """
        
        clean = self.settings.get('services').get('cloudformation', {}).get('stacks', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_stacks().get('Stacks')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('cloudformation', {}).get('stacks', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('StackName')
                resource_date = resource.get('LastUpdatedTime') if resource.get('LastUpdatedTime') is not None else resource.get('CreationTime')

                if resource_id not in self.whitelist.get('cloudformation', {}).get('stack', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.delete_stack(StackName=resource_id)
                            except:
                                self.logging.error("Could not delete Stack '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info("CloudFormation Stack '%s' was last modified %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("CloudFormation Stack '%s' was last modified %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("CloudFormation Stack '%s' has been whitelisted and has not been deleted." % (resource_id))
                    
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'CloudFormation', {}).setdefault(
                            'Stacks', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of CloudFormation Stacks.")
        