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

class Lambda:
    def __init__(self, helper, whitelist, settings):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        self.client = boto3.client('lambda')
    
    
    def run(self):
        self.functions()
        self.layers()
        
    def functions(self):
        """
        Deletes Lambda Functions.
        """
        ttl_days = int(self.settings.get('resource', {}).get('lambda_function_ttl_days', 7))
        resources = self.client.list_functions().get('Functions')
        
        for resource in resources:
            resource_id = resource.get('FunctionName')
            resource_date = resource.get('LastModified')

            if resource_id not in self.whitelist.get('lambda', {}).get('function', []):
                delta = self.helper.get_day_delta(resource_date)
            
                if delta.days > ttl_days: 
                    if self.dry_run == 'false':
                        try:
                            self.client.delete_function(FunctionName=resource_id)
                        except ValueError as e:
                            logging.critical(str(e))
                        except:
                            logging.critical(str(sys.exc_info()))
                    
                    logging.info("Lambda Function '%s' was last modified %d days ago and has been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("Lambda Function '%s' was last modified %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
            else:
                logging.debug("Lambda Function '%s' has been whitelisted and has not been deleted." % (resource_id))
    
    
    def layers(self):
        pass