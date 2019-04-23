import boto3
import sys

from lambda_helper import *


class DynamoDBCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('dynamodb', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))
    
    
    def run(self):
        self.tables()
    

    def tables(self):
        """
        Deletes DynamoDB Tables.
        """
        
        clean = self.settings.get('services').get('dynamodb', {}).get('tables', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.list_tables().get('TableNames')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('dynamodb', {}).get('tables', {}).get('ttl', 7)
            
            for resource in resources:
                resource_date = self.client.describe_table(TableName=resource).get('Table').get('CreationDateTime')

                if resource not in self.whitelist.get('dynamodb', {}).get('table', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.delete_table(TableName=resource)
                            except:
                                self.logging.error("Could not delete DynamoDB Table '%s'." % resource)
                                self.logging.error(str(sys.exc_info()))
                                break
                        
                        self.logging.info(("DynamoDB Table '%s' was created %d days ago "
                                           "and has been deleted.") % (resource, delta.days))
                    else:
                        self.logging.debug(("DynamoDB Table '%s' was created %d days ago "
                                            "(less than TTL setting) and has not been deleted.") % (resource, delta.days))
                else:
                    self.logging.debug(("DynamoDB Table '%s' has been whitelisted and has not "
                                        "been deleted.") % (resource))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'DynamoDB', {}).setdefault(
                            'Tables', []).append(resource)
        else:
            self.logging.debug("Skipping cleanup of DynamoDB Tables.")