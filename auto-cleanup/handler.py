import boto3
import datetime
import dateutil.parser
import json
import logging
import os
import sys

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

            # CloudFormation
            cloudformation_class = CloudFormation(helper_class, whitelist, settings, region)
            cloudformation_class.run()

            # DynamoDB
            dynamodb_class = DynamoDB(helper_class, whitelist, settings, region)
            dynamodb_class.run()
            
            # EC2
            ec2_class = EC2(helper_class, whitelist, settings, region)
            ec2_class.run()
            
            # Lambda
            lambda_class = Lambda(helper_class, whitelist, settings, region)
            lambda_class.run()
            
            # RDS
            rds_class = RDS(helper_class, whitelist, settings, region)
            rds_class.run()

            # Redshift
            redshift_class = Redshift(helper_class, whitelist, settings, region)
            redshift_class.run()
        else:
            logging.debug("Skipping region '%s'." % region)
        
    logging.info("Switching region to 'global'.")

    # S3
    s3_class = S3(helper_class, whitelist, settings)
    s3_class.run()

    logging.info("Auto Cleanup completed.")


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
            client.put_item(TableName=os.environ['WHITELISTTABLE'], Item=whitelist)
    except:
        logging.critical(str(sys.exc_info()))