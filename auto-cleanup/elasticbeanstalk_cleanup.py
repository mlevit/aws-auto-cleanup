import boto3
import sys

from lambda_helper import *


class ElasticBeanstalkCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region
        
        try:
            self.client = boto3.client('elasticbeanstalk', region_name=region)
        except:
            self.logging.error(str(sys.exc_info()))


    def run(self):
        self.applications()


    def applications(self):
        """
        Deletes Elastic Beanstalk Applications.
        """
        
        clean = self.settings.get('services').get('elasticbeanstalk', {}).get('applications', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.describe_applications().get('Applications')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('elasticbeanstalk', {}).get('applications', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('ApplicationName')
                resource_date = resource.get('DateUpdated')

                if resource_id not in self.whitelist.get('elasticbeanstalk', {}).get('application', []):
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        if not self.settings.get('general', {}).get('dry_run', True):
                            try:
                                self.client.delete_application(
                                    ApplicationName=resource_id,
                                    TerminateEnvByForce=True)
                            except:
                                self.logging.error("Could not delete Elastic Beanstalk Application '%s'." % resource_id)
                                self.logging.error(str(sys.exc_info()))
                                continue
                        
                        self.logging.info(("Elastic Beanstalk Application '%s' was last modified %d days ago "
                                           "and has been deleted.") % (resource_id, delta.days))
                    else:
                        self.logging.debug(("Elastic Beanstalk Application '%s' was last modified %d days ago "
                                            "(less than TTL setting) and has not been deleted.") % (resource_id, delta.days))
                else:
                    self.logging.debug("Elastic Beanstalk Application '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'Elastic Beanstalk', {}).setdefault(
                            'Applications', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of Elastic Beanstalk Applications.")