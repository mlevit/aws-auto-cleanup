import boto3
import sys
import time

from lambda_helper import *


class IAMCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = 'global'
        
        try:
            self.client = boto3.client('iam')
        except:
            self.logging.error(str(sys.exc_info()))


    def run(self):
        self.roles()


    def roles(self):
        """
        Deletes IAM Roles.
        """
        
        clean = self.settings.get('services').get('iam', {}).get('roles', {}).get('clean', False)
        if clean:
            try:
                resources = self.client.list_roles().get('Roles')
            except:
                self.logging.error(str(sys.exc_info()))
                return None
            
            ttl_days = self.settings.get('services').get('iam', {}).get('roles', {}).get('ttl', 7)
            
            for resource in resources:
                resource_id = resource.get('RoleName')
                resource_arn = resource.get('Arn')
                resource_date = resource.get('CreateDate')

                if resource_id not in self.whitelist.get('iam', {}).get('role', []) and 'AWSServiceRoleFor' not in resource_id:
                    delta = LambdaHelper.get_day_delta(resource_date)
                
                    if delta.days > ttl_days:
                        # check when the role was last accessed
                        try:
                            gen_last_accessed = self.client.generate_service_last_accessed_details(Arn=resource_arn)
                        except:
                            self.logging.error("Could not generate IAM Role last accessed details for '%s'." % resource_arn)
                            self.logging.error(str(sys.exc_info()))
                            continue
                        
                        try:
                            get_last_accessed = self.client.get_service_last_accessed_details(JobId=gen_last_accessed.get('JobId'))
                        except:
                            self.logging.error("Could not get IAM Role last accessed details for '%s'." % resource_arn)
                            self.logging.error(str(sys.exc_info()))
                            continue
                        
                        backoff = 1
                        while get_last_accessed.get('JobStatus') == 'IN_PROGRESS':
                            if backoff <= 16:
                                time.sleep(backoff)

                                try:
                                    get_last_accessed = self.client.get_service_last_accessed_details(JobId=gen_last_accessed.get('JobId'))
                                except:
                                    self.logging.error("Could not get IAM Role last accessed details for '%s'." % resource_arn)
                                    self.logging.error(str(sys.exc_info()))
                                    continue
                                
                                backoff = 2 * backoff
                            else:
                                self.logging.error(("Could not retrieve IAM Role '%s' last accessed "
                                                    "details in a reasonable amount of time.") % resource_id)
                                return None
                        
                        if get_last_accessed.get('JobStatus') == 'COMPLETED':
                            last_accessed = datetime.datetime.now() - datetime.timedelta(days=365)
                            
                            for service in get_last_accessed.get('ServicesLastAccessed'):
                                service_date = service.get('LastAuthenticated', '1900-01-01 00:00:00')

                                if LambdaHelper.convert_to_datetime(service_date) > LambdaHelper.convert_to_datetime(last_accessed):
                                    last_accessed = service_date
                                
                            delta = LambdaHelper.get_day_delta(last_accessed)
                            
                            if delta.days > ttl_days:
                                if not self.settings.get('general', {}).get('dry_run', True):
                                    # delete all inline policies
                                    try:
                                        policies = self.client.list_role_policies(RoleName=resource_id)
                                    except:
                                        self.logging.error("Could not retrieve inline IAM Policies for IAM Role '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        continue
                                    
                                    for policy in policies.get('PolicyNames'):
                                        try:
                                            self.client.delete_role_policy(
                                                RoleName=resource_id,
                                                PolicyName=policy)

                                            self.logging.info("IAM Policy '%s' has been deleted from IAM Role '%s'." % (policy, resource_id))
                                        except:
                                            self.logging.error("Could not delete an inline IAM Policy '%s' from IAM Role '%s'." % (policy, resource_id))
                                            self.logging.error(str(sys.exc_info()))
                                            continue
                                    
                                    # detach all managed policies
                                    try:
                                        policies = self.client.list_attached_role_policies(RoleName=resource_id)
                                    except:
                                        self.logging.error("Could not retrieve managed IAM Policies attached to IAM Role '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        continue
                                    
                                    for policy in policies.get('AttachedPolicies'):
                                        try:
                                            self.client.detach_role_policy(
                                                RoleName=resource_id,
                                                PolicyArn=policy.get('PolicyArn'))

                                            self.logging.info("IAM Policy '%s' has been detached from IAM Role '%s'." % (policy.get('PolicyName'), resource_id))
                                        except:
                                            self.logging.error("Could not detach a managed IAM Policy '%s' from IAM Role '%s'." % (policy.get('PolicyName'), resource_id))
                                            self.logging.error(str(sys.exc_info()))
                                            continue
                                    
                                    # delete all instance profiles
                                    try:
                                        profiles = self.client.list_instance_profiles_for_role(RoleName=resource_id)
                                    except:
                                        self.logging.error("Could not retrieve IAM Instance Profiles associated with IAM Role '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        continue
                                    
                                    for profile in profiles.get('InstanceProfiles'):
                                        # remove role from instance profile
                                        try:
                                            self.client.remove_role_from_instance_profile(
                                                InstanceProfileName=profile.get('InstanceProfileName'),
                                                RoleName=resource_id)
                                            
                                            self.logging.info("IAM Role '%s' has been removed from IAM Instance Profile '%s'." % (resource_id, profile.get('InstanceProfileName')))
                                        except:
                                            self.logging.error("Could not remove IAM Role '%s' from IAM Instance Profile '%s'." % (resource_id, profile.get('InstanceProfileName')))
                                            self.logging.error(str(sys.exc_info()))
                                            continue
                                        
                                        # delete instance profile
                                        try:
                                            self.client.delete_instance_profile(InstanceProfileName=profile.get('InstanceProfileName'))

                                            self.logging.info("IAM Instance Profile '%s' has been delete." % profile.get('InstanceProfileName'))
                                        except:
                                            self.logging.error("Could not delete IAM Instance Profile '%s'." % profile.get('InstanceProfileName'))
                                            self.logging.error(str(sys.exc_info()))
                                            continue
                                    
                                    # delete role
                                    try:
                                        self.client.delete_role(RoleName=resource_id)
                                    except:
                                        self.logging.error("Could not delete IAM Role '%s'." % resource_id)
                                        self.logging.error(str(sys.exc_info()))
                                        continue
                                
                                self.logging.info(("IAM Role '%s' was last modified %d days ago "
                                                   "and has been deleted.") % (resource_id, delta.days))
                            else:
                                self.logging.debug(("IAM Role '%s' was last accessed %d days ago "
                                                    "(less than TTL setting) and has not been deleted.") % (resource_id, delta.days))
                        else:
                            self.logging.error("Could not get IAM Role last accessed details for '%s'." % resource_id)
                            return None
                    else:
                        self.logging.debug(("IAM Role '%s' was last modified %d days ago "
                                            "(less than TTL setting) and has not been deleted.") % (resource_id, delta.days))
                else:
                    self.logging.debug("IAM Role '%s' has been whitelisted and has not been deleted." % (resource_id))
                
                self.resource_tree.get('AWS').setdefault(
                    self.region, {}).setdefault(
                        'IAM', {}).setdefault(
                            'Roles', []).append(resource_id)
        else:
            self.logging.debug("Skipping cleanup of IAM Roles.")