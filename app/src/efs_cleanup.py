import sys

import boto3

from src.helper import Helper


class EFSCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_efs = None
        self.is_dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_efs(self):
        if not self._client_efs:
            self._client_efs = boto3.client("efs", region_name=self.region)
        return self._client_efs

    def run(self):
        self.file_systems()

    def file_systems(self):
        """
        Deletes EFS File Systems.
        """

        self.logging.debug("Started cleanup of EFS File Systems.")

        clean = (
            self.settings.get("services", {})
            .get("efs", {})
            .get("file_system", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_efs.get_paginator("describe_file_systems")
                resources = paginator.paginate().build_full_result().get("FileSystems")
            except:
                self.logging.error("Could not list all EFS File Systems.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("efs", {})
                .get("file_system", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("FileSystemId")
                resource_date = resource.get("CreationTime")
                resource_number_of_mount_targets = resource.get("NumberOfMountTargets")
                resource_action = None

                if resource_id not in self.whitelist.get("efs", {}).get(
                    "file_system", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
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
                                            f"EFS Mount Target '{mount_target_id}' was deleted for EFS File System {resource_id}."
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
                                    f"EFS File System '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EFS File System '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EFS File System '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

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
