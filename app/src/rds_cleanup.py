import sys

import boto3

from src.helper import Helper


class RDSCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_rds = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_rds(self):
        if not self._client_rds:
            self._client_rds = boto3.client("rds", region_name=self.region)
        return self._client_rds

    def run(self):
        self.instances()
        self.snapshots()

    def instances(self):
        """
        Deletes RDS Instances. If Instance has termination
        protection enabled, the protection will be first disabled
        and then the Instance will be terminated.
        """

        self.logging.debug("Started cleanup of RDS Instances.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.rds.instance.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.rds.instance.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "rds.instance")

        if is_cleaning_enabled:
            try:
                paginator = self.client_rds.get_paginator("describe_db_instances")
                resources = paginator.paginate().build_full_result().get("DBInstances")
            except:
                self.logging.error("Could not list all RDS Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("DBInstanceIdentifier")
                resource_date = resource.get("InstanceCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_id not in resource_whitelist:
                    if resource_age > maximum_resource_age:
                        if resource.get("DeletionProtection"):
                            try:
                                if not self.is_dry_run:
                                    self.client_rds.modify_db_instance(
                                        DBInstanceIdentifier=resource_id,
                                        DeletionProtection=False,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not remove termination protection from RDS Instance '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.debug(
                                    f"RDS Instance '{resource_id}' had delete protection turned on "
                                    "and now has been turned off."
                                )

                        if resource_action != "ERROR":
                            try:
                                if not self.is_dry_run:
                                    self.client_rds.delete_db_instance(
                                        DBInstanceIdentifier=resource_id,
                                        SkipFinalSnapshot=True,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete RDS Instance '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"RDS Instance '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Instance '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"RDS Instance '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "RDS",
                    "Instance",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of RDS Instances.")
            return True
        else:
            self.logging.info("Skipping cleanup of RDS Instances.")
            return True

    def snapshots(self):
        """
        Deletes RDS Snapshots.
        """

        self.logging.debug("Started cleanup of RDS Snapshots.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.rds.snapshot.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.rds.snapshot.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "rds.snapshot")

        if is_cleaning_enabled:
            try:
                paginator = self.client_rds.get_paginator("describe_db_snapshots")
                resources = (
                    paginator.paginate(SnapshotType="manual")
                    .build_full_result()
                    .get("DBSnapshots")
                )
            except:
                self.logging.error("Could not list all RDS Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("DBSnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_id not in resource_whitelist:
                    if resource_age > maximum_resource_age:
                        try:
                            if not self.is_dry_run:
                                self.client_rds.delete_db_snapshot(
                                    DBSnapshotIdentifier=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete RDS Snapshot '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"RDS Snapshot '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Snapshot '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"RDS Snapshot '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "RDS",
                    "Snapshot",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of RDS Snapshots.")
            return True
        else:
            self.logging.debug("Skipping cleanup of RDS Snapshots.")
            return True
