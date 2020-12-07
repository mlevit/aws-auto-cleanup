import datetime
import sys
import time

import boto3

from src.helper import Helper


class IAMCleanup:
    def __init__(self, logging, whitelist, settings, execution_log):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = "global"

        self._client_iam = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_iam(self):
        if not self._client_iam:
            self._client_iam = boto3.client("iam")
        return self._client_iam

    def run(self):
        self.policies()
        self.roles()

    def policies(self):
        """
        Deletes IAM Policies.
        """

        self.logging.debug("Started cleanup of IAM Policies.")

        clean = (
            self.settings.get("services", {})
            .get("iam", {})
            .get("policy", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_iam.get_paginator("list_policies")
                resources = (
                    paginator.paginate(Scope="Local")
                    .build_full_result()
                    .get("Policies")
                )
            except:
                self.logging.error("Could not list all IAM Policies.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("iam", {})
                .get("policy", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("PolicyName")
                resource_arn = resource.get("Arn")
                resource_date = resource.get("UpdateDate")
                resource_action = None

                if resource_id not in self.whitelist.get("iam", {}).get("policy", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource.get("AttachmentCount") > 0:
                            # - Detach the policy from all users, groups, and roles that the policy is attached to,
                            #   using the DetachUserPolicy, DetachGroupPolicy, or DetachRolePolicy API operations.
                            #   To list all the users, groups, and roles that a policy is attached to, use ListEntitiesForPolicy.
                            entities_paginator = self.client_iam.get_paginator(
                                "list_entities_for_policy"
                            )

                            try:
                                user_resources = entities_paginator.paginate(
                                    PolicyArn=resource_arn, EntityFilter="User"
                                ).build_full_result()
                            except:
                                self.logging.error(
                                    f"Could not list all IAM Users with IAM Policy '{resource_id}' attached."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                for user_resource in user_resources.get("PolicyUsers"):
                                    try:
                                        if not self._dry_run:
                                            self.client_iam.detach_user_policy(
                                                UserName=user_resource.get("UserName"),
                                                PolicyArn=resource_arn,
                                            )
                                    except:
                                        self.logging.error(
                                            f"""Could not detatch IAM Policy '{resource_id}' from IAM User {user_resource.get("UserName")}."""
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.debug(
                                            f"""IAM Policy '{resource_id}' was detatched from IAM User {user_resource.get("UserName")}."""
                                        )

                            try:
                                role_resources = entities_paginator.paginate(
                                    PolicyArn=resource_arn, EntityFilter="Role"
                                ).build_full_result()
                            except:
                                self.logging.error(
                                    f"Could not list all IAM Roles with IAM Policy '{resource_id}' attached."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                for role_resource in role_resources.get("PolicyRoles"):
                                    try:
                                        if not self._dry_run:
                                            self.client_iam.detach_role_policy(
                                                RoleName=role_resource.get("RoleName"),
                                                PolicyArn=resource_arn,
                                            )
                                    except:
                                        self.logging.error(
                                            f"""Could not detatch IAM Policy '{resource_id}' from IAM Role {role_resource.get("RoleName")}."""
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.debug(
                                            f"""IAM Policy '{resource_id}' was detatched from IAM Role {role_resource.get("RoleName")}."""
                                        )

                            try:
                                group_resources = entities_paginator.paginate(
                                    PolicyArn=resource_arn, EntityFilter="Group"
                                ).build_full_result()
                            except:
                                self.logging.error(
                                    f"Could not list all IAM Policies with IAM Group '{resource_id}' attached."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                for group_resource in group_resources.get(
                                    "PolicyGroups"
                                ):
                                    try:
                                        if not self._dry_run:
                                            self.client_iam.detach_group_policy(
                                                GroupName=group_resource.get(
                                                    "GroupName"
                                                ),
                                                PolicyArn=resource_arn,
                                            )
                                    except:
                                        self.logging.error(
                                            f"""Could not detatch IAM Policy '{resource_id}' from IAM Group {group_resource.get("GroupName")}."""
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.debug(
                                            f"""IAM Policy '{resource_id}' was detatched from IAM Group {group_resource.get("GroupName")}."""
                                        )

                        # - Delete all versions of the policy using DeletePolicyVersion. To list the policy's versions, use ListPolicyVersions.
                        #   You cannot use DeletePolicyVersion to delete the version that is marked as the default version.
                        #   You delete the policy's default version in the next step of the process.
                        try:
                            versions_paginator = self.client_iam.get_paginator(
                                "list_policy_versions"
                            )
                            versions_resources = versions_paginator.paginate(
                                PolicyArn=resource_arn
                            ).build_full_result()
                        except:
                            self.logging.error(
                                f"Could not list all IAM Policy's '{resource_id}' versions."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            for versions_resource in versions_resources.get("Versions"):
                                if not versions_resource.get("IsDefaultVersion"):
                                    try:
                                        if not self._dry_run:
                                            self.client_iam.delete_policy_version(
                                                PolicyArn=resource_arn,
                                                VersionId=versions_resource.get(
                                                    "VersionId"
                                                ),
                                            )
                                    except:
                                        self.logging.error(
                                            f"""Could not delete IAM Policy Version '{versions_resource.get("VersionId")}' for IAM Policy {resource_id}."""
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.debug(
                                            f"""IAM Policy Version '{versions_resource.get("VersionId")}' was deleted for IAM Policy {resource_id}."""
                                        )

                        # - Delete the policy (this automatically deletes the policy's default version) using this API.
                        try:
                            if not self._dry_run:
                                self.client_iam.delete_policy(PolicyArn=resource_arn)
                        except:
                            self.logging.error(
                                f"Could not delete IAM Policy '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"IAM Policy '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"IAM Policy '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"IAM Policy '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "IAM",
                    "Policy",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of IAM Policies.")
            return True
        else:
            self.logging.info("Skipping cleanup of IAM Policies.")
            return True

    def roles(self):
        """
        Deletes IAM Roles.
        """

        self.logging.debug("Started cleanup of IAM Roles.")

        clean = (
            self.settings.get("services", {})
            .get("iam", {})
            .get("role", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_iam.get_paginator("list_roles")
                resources = paginator.paginate().build_full_result().get("Roles")
            except:
                self.logging.error("Could not list all IAM Roles.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("iam", {})
                .get("role", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("RoleName")
                resource_arn = resource.get("Arn")
                resource_date = resource.get("CreateDate")
                resource_action = None

                if "AWSServiceRoleFor" not in resource_id:
                    if resource_id not in self.whitelist.get("iam", {}).get("role", []):
                        delta = Helper.get_day_delta(resource_date)

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
                                resource_action = "ERROR"
                            else:
                                try:
                                    get_last_accessed = self.client_iam.get_service_last_accessed_details(
                                        JobId=gen_last_accessed.get("JobId")
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not get IAM Role last accessed details for '{resource_arn}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    backoff = 1
                                    while (
                                        get_last_accessed.get("JobStatus")
                                        == "IN_PROGRESS"
                                    ):
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
                                                resource_action = "ERROR"
                                                backoff = 99
                                            else:
                                                backoff = 2 * backoff
                                        else:
                                            self.logging.error(
                                                f"Could not retrieve IAM Role '{resource_id}' last accessed "
                                                "details in a reasonable amount of time."
                                            )
                                            resource_action = "ERROR"

                            if get_last_accessed.get("JobStatus") == "COMPLETED":
                                last_accessed = (
                                    datetime.datetime.now()
                                    - datetime.timedelta(days=365)
                                )

                                for service in get_last_accessed.get(
                                    "ServicesLastAccessed"
                                ):
                                    service_date = service.get(
                                        "LastAuthenticated", "1900-01-01 00:00:00"
                                    )

                                    if Helper.convert_to_datetime(
                                        service_date
                                    ) > Helper.convert_to_datetime(last_accessed):
                                        last_accessed = service_date

                                delta = Helper.get_day_delta(last_accessed)

                                if delta.days > ttl_days:
                                    # delete all inline policies
                                    try:
                                        paginator = self.client_iam.get_paginator(
                                            "list_role_policies"
                                        )
                                        policies = (
                                            paginator.paginate(RoleName=resource_id)
                                            .build_full_result()
                                            .get("PolicyNames")
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve inline IAM Policies for IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                        continue

                                    for policy in policies:
                                        try:
                                            if not self._dry_run:
                                                self.client_iam.delete_role_policy(
                                                    RoleName=resource_id,
                                                    PolicyName=policy,
                                                )
                                        except:
                                            self.logging.error(
                                                f"Could not delete an inline IAM Policy '{policy}' from IAM Role '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            resource_action = "ERROR"
                                        else:
                                            self.logging.debug(
                                                f"IAM Policy '{policy}' has been deleted from IAM Role '{resource_id}'."
                                            )

                                    # detach all managed policies
                                    try:
                                        paginator = self.client_iam.get_paginator(
                                            "list_attached_role_policies"
                                        )
                                        policies = (
                                            paginator.paginate(RoleName=resource_id)
                                            .build_full_result()
                                            .get("AttachedPolicies")
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve managed IAM Policies attached to IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        for policy in policies:
                                            try:
                                                if not self._dry_run:
                                                    self.client_iam.detach_role_policy(
                                                        RoleName=resource_id,
                                                        PolicyArn=policy.get(
                                                            "PolicyArn"
                                                        ),
                                                    )
                                            except:
                                                self.logging.error(
                                                    f"Could not detach a managed IAM Policy '{policy.get('PolicyName')}' from IAM Role '{resource_id}'."
                                                )
                                                self.logging.error(sys.exc_info()[1])
                                                resource_action = "ERROR"
                                            else:
                                                self.logging.debug(
                                                    f"IAM Policy '{policy.get('PolicyName')}' has been detached from IAM Role '{resource_id}'."
                                                )

                                    # delete all instance profiles
                                    try:
                                        paginator = self.client_iam.get_paginator(
                                            "list_instance_profiles_for_role"
                                        )
                                        profiles = (
                                            paginator.paginate(RoleName=resource_id)
                                            .build_full_result()
                                            .get("InstanceProfiles")
                                        )
                                    except:
                                        self.logging.error(
                                            f"Could not retrieve IAM Instance Profiles associated with IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        for profile in profiles:
                                            # remove role from instance profile
                                            try:
                                                if not self._dry_run:
                                                    self.client_iam.remove_role_from_instance_profile(
                                                        InstanceProfileName=profile.get(
                                                            "InstanceProfileName"
                                                        ),
                                                        RoleName=resource_id,
                                                    )
                                            except:
                                                self.logging.error(
                                                    f"Could not remove IAM Role '{resource_id}' from IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                                )
                                                self.logging.error(sys.exc_info()[1])
                                                resource_action = "ERROR"
                                            else:
                                                self.logging.debug(
                                                    f"IAM Role '{resource_id}' has been removed from IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                                )

                                            # delete instance profile
                                            try:
                                                if not self._dry_run:
                                                    self.client_iam.delete_instance_profile(
                                                        InstanceProfileName=profile.get(
                                                            "InstanceProfileName"
                                                        )
                                                    )
                                            except:
                                                self.logging.error(
                                                    f"Could not delete IAM Instance Profile '{profile.get('InstanceProfileName')}'."
                                                )
                                                self.logging.error(sys.exc_info()[1])
                                                resource_action = "ERROR"
                                            else:
                                                self.logging.debug(
                                                    f"IAM Instance Profile '{profile.get('InstanceProfileName')}' has been delete."
                                                )

                                    # delete role
                                    try:
                                        if not self._dry_run:
                                            self.client_iam.delete_role(
                                                RoleName=resource_id
                                            )
                                    except:
                                        self.logging.error(
                                            f"Could not delete IAM Role '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.info(
                                            f"IAM Role '{resource_id}' was created {delta.days} days ago "
                                            "and has been deleted."
                                        )
                                        resource_action = "DELETE"
                                else:
                                    self.logging.debug(
                                        f"IAM Role '{resource_id}' was last accessed {delta.days} days ago "
                                        "(less than TTL setting) and has not been deleted."
                                    )
                                    resource_action = "SKIP - TTL"
                            else:
                                self.logging.error(
                                    f"Could not get IAM Role last accessed details for '{resource_id}'."
                                )
                                resource_action = "ERROR"
                        else:
                            self.logging.debug(
                                f"IAM Role '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"IAM Role '{resource_id}' has been whitelisted and has not been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

                    Helper.record_execution_log_action(
                        self.execution_log,
                        self.region,
                        "IAM",
                        "Role",
                        resource_id,
                        resource_action,
                    )

            self.logging.debug("Finished cleanup of IAM Roles.")
            return True
        else:
            self.logging.info("Skipping cleanup of IAM Roles.")
            return True
