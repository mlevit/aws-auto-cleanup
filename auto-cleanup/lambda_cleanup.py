import boto3
import sys

from lambda_helper import *


class LambdaCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('lambda', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))


    def run(self):
        self.functions()
        self.layers()


    def functions(self):
        """
        Deletes Lambda Functions.
        """
        
        clean = self.settings.get('services').get('lambda', {}).get('functions', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.list_functions().get('Functions')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('lambda', {}).get('functions', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('FunctionName')
                resource_date = resource.get('LastModified')

                if resource_id not in self.whitelist.get('lambda', {}).get('function', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.delete_function(FunctionName=resource_id)
                            except:
                                self.logging.error("Could not delete Lambda Function '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info("Lambda Function '%s' was last modified %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("Lambda Function '%s' was last modified %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("Lambda Function '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'Lambda', {}).setdefault(
                            'Functions', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of Lambda Functions.")


    def layers(self):
        pass