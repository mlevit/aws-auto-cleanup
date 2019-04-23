import boto3
import datetime
import json
import logging
import os
import sys
import tempfile
import threading

from dynamodb_json import json_util as dynamodb_json
from treelib import Tree

from lambda_helper import *
from cloudformation_cleanup import *
from dynamodb_cleanup import *
from ec2_cleanup import *
from emr_cleanup import *
from lambda_cleanup import *
from rds_cleanup import *
from redshift_cleanup import *
from s3_cleanup import *


class Cleanup:
    def __init__(self, logging):
        self.logging = logging

        # insert default values into settings and whitelist tables
        self.setup_dynamodb()
        
        # create dictionaries and variables
        self.resource_tree = {'AWS': {}}
        self.settings = self.get_settings()
        self.whitelist = self.get_whitelist()
        self.dry_run = self.settings.get('general', {}).get('dry_run', True)

        self.run_cleanup()

        self.build_tree(self.resource_tree)
    
    
    def run_cleanup(self):
        if self.dry_run:
            self.logging.info("Auto Cleanup started in DRY RUN mode.")
        else:
            self.logging.info("Auto Cleanup started in DESTROY mode.")
        
        for region in self.settings.get('regions'):
            if self.settings.get('regions').get(region).get('clean'):
                self.logging.info("Switching region to '%s'." % region)

                # threads list
                threads = []

                # CloudFormation
                # CloudFormation will run before all other cleanup operations as there is a potential
                # through the removal of CloudFormation Stacks, many of the other resource will be removed
                cloudformation_class = CloudFormationCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                cloudformation_class.run()

                # DynamoDB
                dynamodb_class = DynamoDBCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                thread = threading.Thread(target=dynamodb_class.run, args=())
                threads.append(thread)

                # EMR
                emr_class = EMRCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                thread = threading.Thread(target=emr_class.run, args=())
                threads.append(thread)
                
                # Lambda
                lambda_class = LambdaCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                thread = threading.Thread(target=lambda_class.run, args=())
                threads.append(thread)
                
                # RDS
                rds_class = RDSCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                thread = threading.Thread(target=rds_class.run, args=())
                threads.append(thread)

                # Redshift
                redshift_class = RedshiftCleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                thread = threading.Thread(target=redshift_class.run, args=())
                threads.append(thread)

                # start all threads
                for thread in threads:
                    thread.start()

                # make sure that all threads have finished
                for thread in threads:
                    thread.join()
                
                # EC2
                # EC2 will run after all other cleanup operations as there is a potential
                # through the removal of other services, EC2 instances will be cleaned up
                ec2_class = EC2Cleanup(self.logging, self.whitelist, self.settings, self.resource_tree, region)
                ec2_class.run()
            else:
                self.logging.debug("Skipping region '%s'." % region)
            
        self.logging.info("Switching region to 'global'.")

        # S3
        s3_class = S3Cleanup(self.logging, self.whitelist, self.settings, self.resource_tree)
        s3_class.run()
        
        self.logging.info("Auto Cleanup completed.")
    
    
    def get_settings(self):
        settings = {}
        try:
            for record in boto3.client('dynamodb').scan(TableName=os.environ['SETTINGSTABLE'])['Items']:
                record_json = dynamodb_json.loads(record, True)
                settings[record_json.get('key')] = record_json.get('value')
        except:
            self.logging.error("Could not read DynamoDB table '%s'." % os.environ['SETTINGSTABLE'])
        
        return settings
    

    def get_whitelist(self):
        whitelist = {}
        try:
            for record in boto3.client('dynamodb').scan(TableName=os.environ['WHITELISTTABLE'])['Items']:
                record_json = dynamodb_json.loads(record, True)
                parsed_resource_id = LambdaHelper.parse_resource_id(record_json.get('resource_id'))
                
                whitelist.setdefault(
                    parsed_resource_id.get('service'), {}).setdefault(
                        parsed_resource_id.get('resource_type'), []).append(
                            parsed_resource_id.get('resource'))
        except:
            self.logging.error("Could not read DynamoDB table '%s'." % os.environ['WHITELISTTABLE'])
        
        return whitelist
    
    
    def setup_dynamodb(self):
        """
        Inserts all the default settings and whitelist data
        into their respective DynamoDB tables. Records will be
        skipped if they already exist in the table.
        """

        try:
            client = boto3.client('dynamodb')
            settings_data = open('data/auto-cleanup-settings.json')
            whitelist_data = open('data/auto-cleanup-whitelist.json')

            settings_json = json.loads(settings_data.read())
            whitelist_json = json.loads(whitelist_data.read())

            update_settings = False
            
            # get current settings version
            current_version = client.get_item(
                TableName=os.environ['SETTINGSTABLE'],
                Key={'key': {'S': 'version'}},
                ConsistentRead=True)
            
            # get new settings version
            new_version = float(settings_json[0].get('value', {}).get('N', 0.0))
            
            # check if settings exist and if they're older than current settings
            if 'Item' in current_version:
                current_version = float(current_version.get('Item').get('value').get('N'))
                if current_version < new_version:
                    update_settings = True
                    self.logging.info("Existing settings with version %s are being updated to version %s in DynamoDB Table '%s'." % (str(current_version), str(new_version), os.environ['SETTINGSTABLE']))
                else:
                    self.logging.debug("Existing settings are at the lastest version %s in DynamoDB Table '%s'." % (str(current_version), os.environ['SETTINGSTABLE']))
            else:
                update_settings = True
                self.logging.info("Settings are being inserted into DynamoDB Table '%s' for the first time." % os.environ['SETTINGSTABLE'])

            if update_settings:
                for setting in settings_json:
                    try:
                        client.put_item(
                            TableName=os.environ['SETTINGSTABLE'],
                            Item=setting)
                    except:
                        self.logging.critical(str(sys.exc_info()))
                        continue
            
            for whitelist in whitelist_json:
                try:
                    client.put_item(
                        TableName=os.environ['WHITELISTTABLE'],
                        Item=whitelist,
                        ConditionExpression="attribute_not_exists(resource_id) AND attribute_not_exists(expire_at)")
                except:
                    continue
        
            settings_data.close()
            whitelist_data.close()
        except:
            self.logging.critical(str(sys.exc_info()))
    
    
    def build_tree(self, resource_tree):
        """
        Build ASCI tree and upload to S3.
        """

        try:
            os.chdir(tempfile.gettempdir())
            tree = Tree()
            
            for aws in resource_tree:
                aws_key = aws
                tree.create_node(aws, aws_key)

                for region in resource_tree.get(aws):
                    region_key = aws_key + region
                    tree.create_node(region, region_key, parent=aws_key)

                    for service in resource_tree.get(aws).get(region):
                        service_key = region_key + service
                        tree.create_node(service, service_key, parent=region_key)

                        for resource_type in resource_tree.get(aws).get(region).get(service):
                            resource_type_key = service_key + resource_type
                            tree.create_node(resource_type, resource_type_key, parent=service_key)

                            for resource in resource_tree.get(aws).get(region).get(service).get(resource_type):
                                resource_key = resource_type_key + resource
                                tree.create_node(resource, resource_key, parent=resource_type_key)
            
            try:
                _, temp_file = tempfile.mkstemp()
            
                try:
                    tree.save2file(temp_file)
                except:
                    self.logging.error("Could not generate resource tree.")
                    return None

                client = boto3.client('s3')
                bucket = os.environ['RESOURCETREEBUCKET']
                key = 'resource_tree_%s.txt' % datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                
                try:
                    client.upload_file(temp_file, bucket, key)
                except:
                    self.logging.error("Could not upload resource tree to S3 's3://%s/%s'." % (bucket, key))
                    return None

                self.logging.info("Resource tree has been built and uploaded to S3 's3://%s/%s'." % (bucket, key))
            finally:
                os.remove(temp_file)
        except:
            self.logging.critical(str(sys.exc_info()))


def lambda_handler(event, context):
    # enable logging
    root = logging.getLogger()

    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.basicConfig(format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)", level=os.environ.get('LOGLEVEL', 'WARNING').upper())

    Cleanup(logging)