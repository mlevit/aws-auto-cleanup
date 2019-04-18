import boto3
import datetime
import dateutil.parser
import json
import logging
import os
import sys
import threading
import uuid

from multiprocessing import Process, Pipe
from treelib import Node, Tree

from helper import *
from cloudformation_handler import *
from dynamodb_handler import *
from ec2_handler import *
from lambda_handler import *
from rds_handler import *
from redshift_handler import *
from s3_handler import *

# enable logging
root = logging.getLogger()

if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.basicConfig(format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)", level=os.environ.get('LOGLEVEL', 'WARNING').upper())


def handler(event, context):
    setup()
    
    tree = {'AWS': {}}
    whitelist = {}
    settings = {}
    
    # build list of whitelisted resources
    for record in boto3.client('dynamodb').scan(TableName=os.environ['WHITELISTTABLE'])['Items']:
        parsed_resource_id = Helper.parse_resource_id(record['resource_id']['S'])
        
        whitelist.setdefault(
            parsed_resource_id.get('service'), {}).setdefault(
                parsed_resource_id.get('resource_type'), []).append(
                    parsed_resource_id.get('resource'))
    
    # build dictionary of settings
    for record in boto3.client('dynamodb').scan(TableName=os.environ['SETTINGSTABLE'])['Items']:
        settings.setdefault(record['category']['S'], {})[record['key']['S']] = record['value']['S']
    
    helper_class = Helper(settings)

    if settings.get('general', {}).get('dry_run', 'true') == 'true':
        logging.info("Auto Cleanup started in DRY RUN mode.")
    else:
        logging.info("Auto Cleanup started in DESTROY mode.")

    for region in settings.get('region'):
        if settings.get('region').get(region) == 'true':
            logging.info("Switching region to '%s'." % region)

            # create a list to keep all processes
            processes = []

            # CloudFormation
            cloudformation_class = CloudFormation(helper_class, whitelist, settings, tree, region)
            process = Process(target=cloudformation_class.run, args=())
            processes.append(process)

            # DynamoDB
            dynamodb_class = DynamoDB(helper_class, whitelist, settings, tree, region)
            process = Process(target=dynamodb_class.run, args=())
            processes.append(process)
            
            # EC2
            ec2_class = EC2(helper_class, whitelist, settings, tree, region)
            process = Process(target=ec2_class.run, args=())
            processes.append(process)
            
            # Lambda
            lambda_class = Lambda(helper_class, whitelist, settings, tree, region)
            process = Process(target=lambda_class.run, args=())
            processes.append(process)
            
            # RDS
            rds_class = RDS(helper_class, whitelist, settings, tree, region)
            process = Process(target=rds_class.run, args=())
            processes.append(process)

            # Redshift
            redshift_class = Redshift(helper_class, whitelist, settings, tree, region)
            process = Process(target=redshift_class.run, args=())
            processes.append(process)

            # start all processes
            for process in processes:
                process.start()

            # make sure that all processes have finished
            for process in processes:
                process.join()

        else:
            logging.debug("Skipping region '%s'." % region)
        
    logging.info("Switching region to 'global'.")

    # S3
    s3_class = S3(helper_class, whitelist, settings, tree)
    s3_class.run()

    
    gen_tree(tree)
    
    logging.info("Auto Cleanup completed.")


def gen_tree(tree_dict):
    os.chdir('/tmp')
    tree = Tree()
    
    for aws in tree_dict:
        aws_key = aws
        tree.create_node(aws, aws_key)

        for region in tree_dict.get(aws):
            region_key = aws_key + region
            tree.create_node(region, region_key, parent=aws_key)

            for service in tree_dict.get(aws).get(region):
                service_key = region_key + service
                tree.create_node(service, service_key, parent=region_key)

                for resource_type in tree_dict.get(aws).get(region).get(service):
                    resource_type_key = service_key + resource_type
                    tree.create_node(resource_type, resource_type_key, parent=service_key)

                    for resource in tree_dict.get(aws).get(region).get(service).get(resource_type):
                        resource_key = resource_type_key + resource
                        tree.create_node(resource, resource_key, parent=resource_type_key)
    
    tree.save2file('/tmp/tree.txt')

    client = boto3.client('s3')
    client.upload_file('/tmp/tree.txt', os.environ['RESOURCETREEBUCKET'], 'resource_tree_%s.txt' % datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))



def setup():
    """
    Inserts all the default settings and whitelist data 
    into their respective DynamoDB tables.
    """

    try:
        client = boto3.client('dynamodb')

        data = open('data/auto-cleanup-settings.json')

        for setting in json.loads(data.read()):
            try:
                client.put_item(
                    TableName=os.environ['SETTINGSTABLE'], 
                    Item=setting,
                    ConditionExpression='attribute_not_exists(#k) AND attribute_not_exists(category)',
                    ExpressionAttributeNames={'#k': 'key'})
            except:
                continue
    
        data = open('data/auto-cleanup-whitelist.json')
        
        for whitelist in json.loads(data.read()):
            try:
                client.put_item(
                    TableName=os.environ['WHITELISTTABLE'], 
                    Item=whitelist,
                    ConditionExpression='attribute_not_exists(resource_id) AND attribute_not_exists(expire_at)')
            except:
                continue
    except:
        logging.critical(str(sys.exc_info()))