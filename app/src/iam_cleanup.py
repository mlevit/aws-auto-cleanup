import datetime
import sys
import time

import boto3

from src.helper import Helper


class IAMCleanup:
    def __init__(self, logging, allowlist, settings, execution_log):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = "global"

        self._client_iam = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_iam(self):
        if not self._client_iam:
            self._client_iam = boto3.client("iam")
        return self._client_iam

    def run(self):
        self.policies()
        self.roles()
        self.users()

    def access_keys(self, user):
        """Deletes IAM Access Keys for a User."""
        self.logging.debug(f"Started cleanup of IAM Access Keys for IAM User '{user}'.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.iam.access_key.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.iam.access_key.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "iam.access_key")

        if is_cleaning_enabled:
            try:
                paginator = self.client_iam.get_paginator("list_access_keys")
                resources = (
                    paginator.paginate(UserName=user)
                    .build_full_result()
                    .get("AccessKeyMetadata")
                )
            except:
                self.logging.error(
                    f"Could not list all IAM Access Keys for IAM User '{user}'."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("AccessKeyId")
                resource_status = resource.get("Status")

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    try:
                        resource_details = self.client_iam.get_access_key_last_used(
                            AccessKeyId=resource_id
                        ).get("AccessKeyLastUsed")
                    except:
                        self.logging.error(
                            f"Could not get IAM Access Key's '{resource_id}' details."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        resource_date = resource_details.get(
                            "resource_details", resource.get("CreateDate")
                        )
                        resource_age = Helper.get_day_delta(resource_date).days
                        resource_action = None

                        if resource_status == "Inactive":
                            try:
                                if not self.is_dry_run:
                                    self.client_iam.delete_access_key(
                                        UserName=user, AccessKeyId=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete IAM Access Key '{resource_id}' for IAM User '{user}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"IAM Access Key '{resource_id}' for IAM User '{user}' in state '{resource_status}' has been deleted."
                                )
                                resource_action = "DELETE"
                        elif resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_iam.delete_access_key(
                                        UserName=user, AccessKeyId=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete IAM Access Key '{resource_id}' for IAM User '{user}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"IAM Access Key '{resource_id}' for IAM User '{user}' was "
                                    f"last used {resource_age} days ago and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"IAM Access Key '{resource_id}' for IAM User '{user}' was last "
                                f"used {resource_age} days ago (less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"IAM Access Key '{resource_id}' for IAM User '{user}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "IAM",
                    "Access Key",
                    resource_id,
                    resource_action,
                )

            self.logging.debug(
                f"Finished cleanup of IAM Access Keys for IAM User '{user}'."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of IAM Access Keys for IAM User '{user}'."
            )
            return True

    def policies(self):
        """Deletes IAM Policies."""
        self.logging.debug("Started cleanup of IAM Policies.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.iam.policy.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.iam.policy.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "iam.policy")

        if is_cleaning_enabled:
            try:
                paginator = self.client_iam.get_paginator("list_policies")
                resources = paginator.paginate(Scope="Local").build_full_result()[
                    "Policies"
                ]
            except:
                self.logging.error("Could not list all IAM Policies.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("PolicyName")
                resource_arn = resource.get("Arn")
                resource_date = resource.get("UpdateDate")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
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
                                        if not self.is_dry_run:
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
                                        if not self.is_dry_run:
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
                                        if not self.is_dry_run:
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
                                        if not self.is_dry_run:
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
                            if not self.is_dry_run:
                                self.client_iam.delete_policy(PolicyArn=resource_arn)
                        except:
                            self.logging.error(
                                f"Could not delete IAM Policy '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"IAM Policy '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"IAM Policy '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"IAM Policy '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes IAM Roles."""
        self.logging.debug("Started cleanup of IAM Roles.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.iam.role.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.iam.role.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "iam.role")

        if is_cleaning_enabled:
            try:
                paginator = self.client_iam.get_paginator("list_roles")
                resources = paginator.paginate().build_full_result().get("Roles")
            except:
                self.logging.error("Could not list all IAM Roles.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("RoleName")
                resource_arn = resource.get("Arn")
                resource_date = resource.get("CreateDate")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if "AWSServiceRoleFor" not in resource_id:
                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
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
                                                continue
                                            else:
                                                backoff = 2 * backoff
                                        else:
                                            self.logging.error(
                                                f"Could not retrieve IAM Role '{resource_id}' last accessed "
                                                "details in a reasonable amount of time."
                                            )
                                            resource_action = "ERROR"
                                            continue

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

                                if resource_age > resource_maximum_age:
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
                                            if not self.is_dry_run:
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
                                                if not self.is_dry_run:
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
                                                if not self.is_dry_run:
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
                                                if not self.is_dry_run:
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
                                        if not self.is_dry_run:
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
                                            f"IAM Role '{resource_id}' was created {resource_age} days ago "
                                            "and has been deleted."
                                        )
                                        resource_action = "DELETE"
                                else:
                                    self.logging.debug(
                                        f"IAM Role '{resource_id}' was last accessed {resource_age} days ago "
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
                                f"IAM Role '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"IAM Role '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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

    def user_policies(self, user):
        """Deletes IAM User Policies."""
        self.logging.debug(
            f"Started cleanup of IAM User Policies for IAM User '{user}'."
        )

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.iam.user_policy.clean", False
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "iam.user_policy")

        if is_cleaning_enabled:
            try:
                paginator = self.client_iam.get_paginator("list_user_policies")
                resources = (
                    paginator.paginate(UserName=user)
                    .build_full_result()
                    .get("PolicyNames")
                )
            except:
                self.logging.error(
                    f"Could not list all IAM User Policies for IAM User '{user}'."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    try:
                        if not self.is_dry_run:
                            self.client_iam.delete_user_policy(
                                UserName=user, PolicyName=resource_id
                            )
                    except:
                        self.logging.error(
                            f"Could not delete IAM User Policy '{resource_id}' for IAM User '{user}'."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        self.logging.info(
                            f"IAM User Policy '{resource_id}' for IAM User '{user}' has been deleted."
                        )
                        resource_action = "DELETE"
                else:
                    self.logging.debug(
                        f"IAM User Policy '{resource_id}' for IAM User '{user}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "IAM",
                    "User Policy",
                    resource_id,
                    resource_action,
                )

            self.logging.debug(
                f"Finished cleanup of IAM User Policies for IAM User '{user}'."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of IAM User Policies for IAM User '{user}'."
            )
            return True

    def delete_login_profile(self, user):
        """Deletes IAM Login Profile."""
        try:
            if not self.is_dry_run:
                self.client_iam.delete_login_profile(UserName=user)
        except self.client_iam.exceptions.NoSuchEntityException:
            self.logging.debug(f"No Login Profile to delete for IAM User '{user}'.")
            return True
        except:
            self.logging.error(f"Could not delete IAM User '{user}' Login Profile.")
            self.logging.error(sys.exc_info()[1])
            return False
        else:
            self.logging.debug(f"Deleted Login Profile for IAM User '{user}'.")
            return True

    def remove_user_from_group(self, user):
        """Removes IAM User from IAM Group."""
        try:
            paginator = self.client_iam.get_paginator("list_groups_for_user")
            resources = (
                paginator.paginate(UserName=user).build_full_result().get("Groups")
            )
        except:
            self.logging.error(f"Could not list all IAM Groups for IAM User '{user}'.")
            self.logging.error(sys.exc_info()[1])
            return False

        for resource in resources:
            resource_id = resource.get("GroupName")

            try:
                self.client_iam.remove_user_from_group(
                    GroupName=resource_id, UserName=user
                )
            except:
                self.logging.error(
                    f"Could not remove IAM User '{user}' from IAM Group '{resource_id}'."
                )
                self.logging.error(sys.exc_info()[1])
            else:
                self.logging.debug(
                    f"Removed IAM User '{user}' from IAM Group '{resource_id}'."
                )

            return True

    def users(self):
        """
        Deletes IAM Users.

        Before attempting to delete a user, remove the following items:

          ☑ Password ( DeleteLoginProfile )
          ☑ Access keys ( DeleteAccessKey )
          ☐ Signing certificate ( DeleteSigningCertificate )
          ☐ SSH public key ( DeleteSSHPublicKey )
          ☐ Git credentials ( DeleteServiceSpecificCredential )
          ☐ Multi-factor authentication (MFA) device ( DeactivateMFADevice , DeleteVirtualMFADevice )
          ☑ Inline policies ( DeleteUserPolicy )
          ☑ Attached managed policies ( DetachUserPolicy )
          ☑ Group memberships ( RemoveUserFromGroup )
        """
        self.logging.debug("Started cleanup of IAM Users.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.iam.user.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.iam.user.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "iam.user")

        if is_cleaning_enabled:
            try:
                paginator = self.client_iam.get_paginator("list_users")
                resources = paginator.paginate().build_full_result().get("Users")
            except:
                self.logging.error("Could not list all IAM Users.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("UserName")
                resource_date = resource.get(
                    "PasswordLastUsed", resource.get("CreateDate")
                )
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        self.access_keys(resource_id)
                        self.delete_login_profile(resource_id)
                        self.remove_user_from_group(resource_id)
                        self.user_policies(resource_id)

                        try:
                            if not self.is_dry_run:
                                self.client_iam.delete_user(UserName=resource_id)
                        except self.client_iam.exceptions.DeleteConflictException:
                            self.logging.debug(
                                f"IAM User '{resource_id}' has dependent objects and has not been deleted."
                            )
                            resource_action = "SKIP - IN USE"
                        except:
                            self.logging.error(
                                f"Could not delete IAM User '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"IAM User '{resource_id}' was last used {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"IAM User '{resource_id}' was last used {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"IAM User '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "IAM",
                    "User",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of IAM Users.")
            return True
        else:
            self.logging.info("Skipping cleanup of IAM Users.")
            return True
