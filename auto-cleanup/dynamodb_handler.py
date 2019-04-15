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
    def __init__(self, helper, whitelist, settings):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        self.client = boto3.client('dynamodb')
    
    
    def run(self):
        self.tables()
    

    def tables(self):
        """
        Deletes DynamoDB Tables.
        """
        ttl_days = int(self.settings.get('resource', {}).get('dynamodb_table_ttl_days', 7))
        resources = self.client.list_tables().get('TableNames')
        
        for resource in resources:
                resource_date = self.client.describe_table(TableName=resource).get('Table').get('CreationDateTime')

                if resource not in self.whitelist.get('dynamodb', {}).get('table', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if self.dry_run == 'false':
                            try:
                                self.client.delete_table(TableName=resource)
                            except ValueError as e:
                                logging.critical(str(e))
                            except:
                                logging.critical(str(sys.exc_info()))
                        
                        logging.info("DynamoDB Table '%s' was created %d days ago and has been deleted." % (resource, delta.days))
                    else:
                        logging.debug("DynamoDB Table '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource, delta.days))
                else:
                    logging.debug("DynamoDB Table '%s' has been whitelisted and has not been deleted." % (resource))