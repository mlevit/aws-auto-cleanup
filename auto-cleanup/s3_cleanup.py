import boto3
import os
import sys

from lambda_helper import *


class S3Cleanup:
    def __init__(self, logging, whitelist, settings, resource_tree):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = 'global'
        
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

        clean = self.settings.get('services').get('s3', {}).get('buckets', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.list_buckets()
            except:
                logging.critical(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('s3', {}).get('buckets', {}).get('ttl', 7)
            
            for resource in resources.get('Buckets'):
                resource_id = resource.get('Name')
                resource_date = resource.get('CreationDate')

                if resource_id not in self.whitelist.get('s3', {}).get('bucket', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            # delete all objects
                            try:
                                response = self.client.list_objects_v2(Bucket=resource_id)
                            except:
                                self.logging.error("Could not retrieve all Objects from Bucket '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break

                            while response.get('KeyCount') > 0:
                                self.logging.debug("S3 Bucket '%s' has %d Objects that have been deleted." % (resource_id, len(response.get('Contents'))))
                                
                                try:
                                    self.client.delete_objects(
                                        Bucket=resource_id,
                                        Delete={
                                            'Objects': [{'Key':obj.get('Key')} for obj in response.get('Contents')],
                                            'Quiet': True})
                                except:
                                    self.logging.error("Could not delete Objects from Bucket '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                
                                response = self.client.list_objects_v2(Bucket=resource_id)
                        
                            # delete all Versions and DeleteMarkers
                            try:
                                response = self.client.get_paginator('list_object_versions')
                            except:
                                self.logging.error("Could not get all Versions and Delete Markers from Bucket '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                break

                            delete_list = []
                            
                            for response_object in response.paginate(Bucket=resource_id):
                                if 'DeleteMarkers' in response_object:
                                    for delete_marker in response_object.get('DeleteMarkers'):
                                        delete_list.append({'Key': delete_marker['Key'], 'VersionId': delete_marker['VersionId']})

                                if 'Versions' in response_object:
                                    for version in response_object['Versions']:
                                        delete_list.append({'Key': version['Key'], 'VersionId': version['VersionId']})
                            
                            self.logging.debug("S3 Bucket '%s' has %d Versions / Delete Markers that have been deleted." % (resource_id, len(delete_list)))

                            for i in range(0, len(delete_list), 1000):
                                try:
                                    self.client.delete_objects(
                                        Bucket=resource_id,
                                        Delete={
                                            'Objects': delete_list[i:i+1000],
                                            'Quiet': True})
                                except:
                                    self.logging.error("Could not delete Versions and Delete Markers from Bucket '%s'." % resource_id)
                                    self.logging.error(str(sys.exc_info()))
                                    break
                            
                            # delete bucket
                            try:
                                self.client.delete_bucket(Bucket=resource_id)
                            except:
                                self.logging.error("Could not delete Bucket '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                        
                        self.logging.info("S3 Bucket '%s' was created %d days ago and has been deleted." % (resource_id, delta.days))
                    else:
                        self.logging.debug("S3 Bucket '%s' was created %d days ago (less than TTL setting) and has not been deleted." % (resource_id, delta.days))
                else:
                    self.logging.debug("S3 Bucket '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'S3', {}).setdefault(
                            'Buckets', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of S3 Buckets.")