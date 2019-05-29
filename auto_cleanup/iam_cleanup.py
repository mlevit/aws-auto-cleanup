import datetime
import sys
import time

import boto3

from . import lambda_helper


class IAMCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = "global"

        self._client_iam = None

    @property
    def client_iam(self):
        if not self._client_iam:
            self._client_iam = boto3.client("iam")
        return self._client_iam

    def run(self):
        self.roles()

    def roles(self):
        """
        Deletes IAM Roles.
        """

        clean = (
            self.settings.get("services", {})
            .get("iam", {})
            .get("roles", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_iam.list_roles().get("Roles")
            except:
                self.logging.error("Could not list all IAM Roles.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("iam", {})
                .get("roles", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("RoleName")
                resource_arn = resource.get("Arn")
                resource_date = resource.get("CreateDate")

                if (
                    resource_id not in self.whitelist.get("iam", {}).get("role", [])
                    and "AWSServiceRoleFor" not in resource_id
                ):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        # check when the role was last accessed
                        try:
                            gen_last_accessed = self.client_iam.generate_service_last_accessed_details(
                                Arn=resource_arn
                            )
                        except:
                            self.logging.error(
                                f"Could not generate IAM Role last accessed details for '{resource_arn}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            continue

                        try:
                            get_last_accessed = self.client_iam.get_service_last_accessed_details(
                                JobId=gen_last_accessed.get("JobId")
                            )
                        except:
                            self.logging.error(
                                f"Could not get IAM Role last accessed details for '{resource_arn}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            continue

                        backoff = 1
                        while get_last_accessed.get("JobStatus") == "IN_PROGRESS":
                            if backoff <= 16:
                                time.sleep(backoff)

                                try:
                                    get_last_accessed = self.client_iam.get_service_last_accessed_details(
                                        JobId=gen_last_accessed.get("JobId")
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not get IAM Role last accessed details for '{resource_arn}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    continue

                                backoff = 2 * backoff
                            else:
                                self.logging.error(
                                    f"Could not retrieve IAM Role '{resource_id}' last accessed "
                                    "details in a reasonable amount of time."
                                )
                                return False

                        if get_last_accessed.get("JobStatus") == "COMPLETED":
                            last_accessed = datetime.datetime.now() - datetime.timedelta(
                                days=365
                            )

                            for service in get_last_accessed.get(
                                "ServicesLastAccessed"
                            ):
                                service_date = service.get(
                                    "LastAuthenticated", "1900-01-01 00:00:00"
                                )

                                if lambda_helper.LambdaHelper.convert_to_datetime(
                                    service_date
                                ) > lambda_helper.LambdaHelper.convert_to_datetime(last_accessed):
                                    last_accessed = service_date

                            delta = lambda_helper.LambdaHelper.get_day_delta(last_accessed)

                            if delta.days > ttl_days:
                                if not self.settings.get("general", {}).get(
                                    "dry_run", True
                                ):
                                    # delete all inline policies
                                    try:
                                        policies = self.client_iam.list_role_policies(
                                            RoleName=resource_id
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve inline IAM Policies for IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        continue

                                    for policy in policies.get("PolicyNames"):
                                        try:
                                            self.client_iam.delete_role_policy(
                                                RoleName=resource_id, PolicyName=policy
                                            )

                                            self.logging.info(
                                                f"IAM Policy '{policy}' has been deleted from IAM Role '{resource_id}'."
                                            )
                                        except:
                                            self.logging.error(
                                                f"Could not delete an inline IAM Policy '{policy}' from IAM Role '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            continue

                                    # detach all managed policies
                                    try:
                                        policies = self.client_iam.list_attached_role_policies(
                                            RoleName=resource_id
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve managed IAM Policies attached to IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        continue

                                    for policy in policies.get("AttachedPolicies"):
                                        try:
                                            self.client_iam.detach_role_policy(
                                                RoleName=resource_id,
                                                PolicyArn=policy.get("PolicyArn"),
                                            )

                                            self.logging.info(
                                                f"IAM Policy '{policy.get('PolicyName')}' has been detached from IAM Role '{resource_id}'."
                                            )
                                        except:
                                            self.logging.error(
                                                f"Could not detach a managed IAM Policy '{policy.get('PolicyName')}' from IAM Role '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            continue

                                    # delete all instance profiles
                                    try:
                                        profiles = self.client_iam.list_instance_profiles_for_role(
                                            RoleName=resource_id
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve IAM Instance Profiles associated with IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        continue

                                    for profile in profiles.get("InstanceProfiles"):
                                        # remove role from instance profile
                                        try:
                                            self.client_iam.remove_role_from_instance_profile(
                                                InstanceProfileName=profile.get(
                                                    "InstanceProfileName"
                                                ),
                                                RoleName=resource_id,
                                            )

                                            self.logging.info(
                                                f"IAM Role '{resource_id}' has been removed from IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                            )
                                        except:
                                            self.logging.error(
                                                f"Could not remove IAM Role '{resource_id}' from IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            continue

                                        # delete instance profile
                                        try:
                                            self.client_iam.delete_instance_profile(
                                                InstanceProfileName=profile.get(
                                                    "InstanceProfileName"
                                                )
                                            )

                                            self.logging.info(
                                                f"IAM Instance Profile '{profile.get('InstanceProfileName')}' has been delete."
                                            )
                                        except:
                                            self.logging.error(
                                                f"Could not delete IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            continue

                                    # delete role
                                    try:
                                        self.client_iam.delete_role(
                                            RoleName=resource_id
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not delete IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        continue

                                self.logging.info(
                                    f"IAM Role '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                            else:
                                self.logging.debug(
                                    f"IAM Role '{resource_id}' was last accessed {delta.days} days ago "
                                    "(less than TTL setting) and has not been deleted."
                                )
                        else:
                            self.logging.error(
                                f"Could not get IAM Role last accessed details for '{resource_id}'."
                            )
                            return False
                    else:
                        self.logging.debug(
                            f"IAM Role '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"IAM Role '%s' has been whitelisted and has not been deleted."
                        % (resource_id)
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "IAM", {}
                ).setdefault("Roles", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of IAM Roles.")
            return True
