import sys

import boto3

from src.helper import Helper


class EFSCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_efs = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_efs(self):
        if not self._client_efs:
            self._client_efs = boto3.client("efs", region_name=self.region)
        return self._client_efs

    def run(self):
        self.file_systems()

    def file_systems(self):
        """Deletes EFS File Systems."""
        self.logging.debug("Started cleanup of EFS File Systems.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.efs.file_system.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.efs.file_system.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "efs.file_system")

        if is_cleaning_enabled:
            try:
                paginator = self.client_efs.get_paginator("describe_file_systems")
                resources = paginator.paginate().build_full_result().get("FileSystems")
            except:
                self.logging.error("Could not list all EFS File Systems.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("FileSystemId")
                resource_date = resource.get("CreationTime")
                resource_number_of_mount_targets = resource.get("NumberOfMountTargets")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_number_of_mount_targets > 0:
                            try:
                                resource_mount_targets = (
                                    self.client_efs.describe_mount_targets(
                                        FileSystemId=resource_id
                                    ).get("MountTargets")
                                )
                            except:
                                self.logging.error(
                                    f"Could not list all EFS Mount Targets for EFS File System '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                for mount_target in resource_mount_targets:
                                    mount_target_id = mount_target.get("MountTargetId")

                                    try:
                                        if not self.is_dry_run:
                                            self.client_efs.delete_mount_target(
                                                MountTargetId=mount_target_id
                                            )
                                    except:
                                        self.logging.error(
                                            f"Could not delete EFS Mount Target '{mount_target_id}' from EFS File System '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.info(
                                            f"EFS Mount Target '{mount_target_id}' was deleted for EFS File System '{resource_id}'."
                                        )

                        if resource_action != "ERROR":
                            try:
                                if not self.is_dry_run:
                                    self.client_efs.delete_file_system(
                                        FileSystemId=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete EFS File System '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EFS File System '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EFS File System '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EFS File System '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EFS",
                    "File System",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EFS File Systems.")
            return True
        else:
            self.logging.info("Skipping cleanup of EFS File Systems.")
            return True
