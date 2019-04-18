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


class CloudFormation:
    def __init__(self, helper, whitelist, settings, tree, region):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        self.tree = tree
        self.region = region
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        try:
            self.client = boto3.client('cloudformation', region_name=region)
        except:
            logging.critical(str(sys.exc_info()))
    
    
    def run(self):
        self.stacks()
        
        
    def stacks(self):
        """
        Deletes CloudFormation Stacks.
        """
        
        ttl_days = int(self.settings.get('ttl', {}).get('cloudformation_stack', 7))
        try:
            resources = self.client.describe_stacks().get('Stacks')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_id = resource.get('StackName')
                resource_date = resource.get('LastUpdatedTime') if resource.get('LastUpdatedTime') is not None else resource.get('CreationTime')

                if resource_id not in self.whitelist.get('cloudformation', {}).get('stack', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if self.dry_run == 'false':
                            self.client.delete_stack(StackName=resource_id)
                        
                        logging.info("CloudFormation Stack '%s' was last modified %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("CloudFormation Stack '%s' was last modified %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("CloudFormation Stack '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            self.tree.get('AWS').setdefault(
                self.region, {}).setdefault(
                    'CloudFormation', {}).setdefault(
                        'Stacks', []).append(resource_id)
        