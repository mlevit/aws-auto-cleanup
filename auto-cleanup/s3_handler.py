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


class S3:
    def __init__(self, helper, whitelist, settings, resource_map):
        self.helper = helper
        self.whitelist = whitelist
        self.settings = settings
        self.resource_map = resource_map
        self.region = 'global'
        
        self.dry_run = settings.get('general', {}).get('dry_run', 'true')
        
        try:
            self.client = boto3.client('s3')
        except:
            logging.critical(str(sys.exc_info()))
    
    
    def run(self):
        self.buckets()
        
    
    def buckets(self):
        """
        Deletes Buckets. All Bucket Objects, Versions and Deleted Markers
        are first deleted before the Bucket can be deleted.
        """

        ttl_days = int(self.settings.get('resource', {}).get('s3_bucket_ttl_days', 7))
        try:
            resources = self.client.list_buckets()
        except:
            logging.critical(str(sys.exc_info()))
            return None
        
        for resource in resources.get('Buckets'):
            try:
                resource_id = resource.get('Name')
                resource_date = resource.get('CreationDate')

                self.resource_map.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'S3', {}).setdefault(
                            'Buckets', []).append(resource_id)

                if resource_id not in self.whitelist.get('s3', {}).get('bucket', []):
                    delta = self.helper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days: 
                        if self.dry_run == 'false':
                            # delete all objects
                            response = self.client.list_objects_v2(Bucket=resource_id)

                            while response.get('KeyCount') > 0:
                                logging.debug("S3 Bucket '%s' has %d Objects that have been deleted." % (resource_id, len(response.get('Contents'))))
                                
                                self.client.delete_objects(
                                    Bucket=resource_id,
                                    Delete={
                                        'Objects': [{'Key':obj.get('Key')} for obj in response.get('Contents')],
                                        'Quiet': True})
                                
                                response = self.client.list_objects_v2(Bucket=resource_id)
                        
                            # delete all Versions and DeleteMarkers
                            response = self.client.get_paginator('list_object_versions')

                            delete_list = []
                            
                            for response_object in response.paginate(Bucket=resource_id):
                                if 'DeleteMarkers' in response_object:
                                    for delete_marker in response_object.get('DeleteMarkers'):
                                        delete_list.append({'Key': delete_marker['Key'], 'VersionId': delete_marker['VersionId']})

                                if 'Versions' in response_object:
                                    for version in response_object['Versions']:
                                        delete_list.append({'Key': version['Key'], 'VersionId': version['VersionId']})
                            
                            logging.debug("S3 Bucket '%s' has %d Versions / Delete Markers that have been deleted." % (resource_id, len(delete_list)))

                            for i in range(0, len(delete_list), 1000):
                                self.client.delete_objects(
                                    Bucket=resource_id,
                                    Delete={
                                        'Objects': delete_list[i:i+1000],
                                        'Quiet': True})
                            
                            # delete bucket
                            self.client.delete_bucket(Bucket=resource_id)
                        
                        logging.info("S3 Bucket '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        logging.debug("S3 Bucket '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    logging.debug("S3 Bucket '%s' has been whitelisted and has not been deleted." % (resource_id))
            except:
                logging.critical(str(sys.exc_info()))
            
            return None