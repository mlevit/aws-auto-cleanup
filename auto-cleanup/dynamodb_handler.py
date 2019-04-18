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


class DynamoDB:
    def __init__(self, helper, whitelist, settings, tree, region):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        self.tree = tree
        self.region = region
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        try:
            self.client = boto3.client('dynamodb', region_name=region)
        except:
            logging.critical(str(sys.exc_info()))
    
    
    def run(self):
        self.tables()
    

    def tables(self):
        """
        Deletes DynamoDB Tables.
        """
        ttl_days = int(self.settings.get('resource', {}).get('dynamodb_table_ttl_days', 7))
        try:
            resources = self.client.list_tables().get('TableNames')
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources:
            try:
                resource_date = self.client.describe_table(TableName=resource).get('Table').get('CreationDateTime')

                if resource not in self.whitelist.get('dynamodb', {}).get('table', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if self.dry_run == 'false':
                            self.client.delete_table(TableName=resource)
                        
                        logging.info("DynamoDB Table '%s' was created %d days ago and has been deleted." % (resource, delta.days))
                    else:
                        logging.debug("DynamoDB Table '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource, delta.days))
                else:
                    logging.debug("DynamoDB Table '%s' has been whitelisted and has not been deleted." % (resource))
            except:
                logging.critical(str(sys.exc_info()))
            
            self.tree.get('AWS').setdefault(
                self.region, {}).setdefault(
                    'DynamoDB', {}).setdefault(
                        'Tables', []).append(resource)