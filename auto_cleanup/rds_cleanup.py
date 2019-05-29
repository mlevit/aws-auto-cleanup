import sys

import boto3

from . import lambda_helper


class RDSCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_rds = None

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

        clean = (
            self.settings.get("services", {})
            .get("rds", {})
            .get("instances", {})
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
                .get("instances", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("DBInstanceIdentifier")
                resource_date = resource.get("InstanceCreateTime")

                if resource_id not in self.whitelist.get("rds", {}).get("instance", []):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            # remove termination prodtection
                            if resource.get("DeletionProtection"):
                                try:
                                    self.client_rds.modify_db_instance(
                                        DBInstanceIdentifier=resource_id,
                                        DeletionProtection=False,
                                    )

                                    self.logging.info(
                                        f"RDS Instance '{resource_id}' had delete protection turned on "
                                        "and now has been turned off."
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not remove termination protection from RDS Instance '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    continue

                            # delete instance
                            try:
                                self.client_rds.delete_db_instance(
                                    DBInstanceIdentifier=resource_id,
                                    SkipFinalSnapshot=True,
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete RDS Instance '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                        self.logging.info(
                            f"RDS Instance '{resource_id}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"RDS Instance '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"RDS Instance '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "RDS", {}
                ).setdefault("Instances", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of RDS Instances.")
            return True

    def snapshots(self):
        """
        Deletes RDS Snapshots.
        """

        clean = (
            self.settings.get("services", {})
            .get("rds", {})
            .get("snapshots", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_rds.describe_db_snapshots().get("DBSnapshots")
            except:
                self.logging.error("Could not list all RDS Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("rds", {})
                .get("snapshots", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("DBSnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")

                if resource_id not in self.whitelist.get("rds", {}).get("snapshot", []):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_rds.delete_db_snapshot(
                                    DBSnapshotIdentifier=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete RDS Snapshot '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                        self.logging.info(
                            f"RDS Snapshot '{resource_id}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"RDS Snapshot '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"RDS Snapshot '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "RDS", {}
                ).setdefault("Snapshots", []).append(resource_id)
            return True
        else:
            self.logging.debug("Skipping cleanup of RDS Snapshots.")
            return True
