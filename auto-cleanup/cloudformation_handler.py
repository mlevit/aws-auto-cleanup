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
    def __init__(self, helper, whitelist, settings):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        
        self.dry_run = settings.get('dry_run', 'true')
        
        self.client = boto3.client('cloudformation')
    
    
    def run(self):
        self.stacks()
        
        
    def stacks(self):
        """
        Deletes CloudFormation Stacks.
        """
        ttl_days = int(self.settings.get('cloudformation_stack_ttl_days', 7))
        resources = self.client.describe_stacks().get('Stacks')
        
        for resource in resources:
            resource_id = resource.get('StackName')
            resource_date = resource.get('LastUpdatedTime') if resource.get('LastUpdatedTime') is not None else resource.get('CreationTime')

            if resource_id not in self.whitelist.get('cloudformation', {}).get('stack', []):
                delta = self.helper.get_day_delta(resource_date)
            
                if delta.days > ttl_days: 
                    if self.dry_run == 'false':
                        try:
                            self.client.delete_stack(StackName=resource_id)
                        except ValueError as e:
                            logging.critical(str(e))
                        except:
                            logging.critical(str(sys.exc_info()))
                    
                    logging.info("CloudFormation Stack '%s' was last modified %d days ago and has been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("CloudFormation Stack '%s' was last modified %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
            else:
                logging.debug("CloudFormation Stack '%s' has been whitelisted and has not been deleted." % (resource_id))
        