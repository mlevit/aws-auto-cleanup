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
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

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

        clean = (
            self.settings.get("services", {})
            .get("rds", {})
            .get("instance", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_rds.describe_db_instances().get("DBInstances")
            except:
                self.logging.error("Could not list all RDS Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("rds", {})
                .get("instance", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("DBInstanceIdentifier")
                resource_date = resource.get("InstanceCreateTime")
                resource_action = None

                if resource_id not in self.whitelist.get("rds", {}).get("instance", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource.get("DeletionProtection"):
                            try:
                                if not self._dry_run:
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
                                if not self._dry_run:
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
                                    f"RDS Instance '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Instance '{resource_id}' was created {delta.days} days ago "
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

        clean = (
            self.settings.get("services", {})
            .get("rds", {})
            .get("snapshot", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_rds.describe_db_snapshots(
                    SnapshotType="manual"
                ).get("DBSnapshots")
            except:
                self.logging.error("Could not list all RDS Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("rds", {})
                .get("snapshot", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("DBSnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_action = None

                if resource_id not in self.whitelist.get("rds", {}).get("snapshot", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
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
                                f"RDS Snapshot '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Snapshot '{resource_id}' was created {delta.days} days ago "
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
