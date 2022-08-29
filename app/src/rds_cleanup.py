import sys

import boto3

from src.helper import Helper


class RDSCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
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
        self.clusters()
        self.cluster_snapshots()
        self.instances()
        self.snapshots()

    def clusters(self):
        """
        Deletes RDS Clusters. If Cluster has termination
        protection enabled, the protection will be first disabled
        and then the Cluster will be terminated.
        """
        self.logging.debug("Started cleanup of RDS Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.rds.cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.rds.cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "rds.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_rds.get_paginator("describe_db_clusters")
                resources = paginator.paginate().build_full_result().get("DBClusters")
            except:
                self.logging.error("Could not list all RDS Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("DBClusterIdentifier")
                resource_date = resource.get("ClusterCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource.get("DeletionProtection"):
                            try:
                                if not self.is_dry_run:
                                    self.client_rds.modify_db_cluster(
                                        DBClusterIdentifier=resource_id,
                                        DeletionProtection=False,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not remove termination protection from RDS Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.debug(
                                    f"RDS Cluster '{resource_id}' had delete protection turned on "
                                    "and now has been turned off."
                                )

                        if resource_action != "ERROR":
                            subresources = resource.get("DBClusterMembers")

                            # Delete all DB Instances in Cluster
                            for subresource in subresources:
                                subresource_id = subresource.get("DBInstanceIdentifier")

                                try:
                                    if not self.is_dry_run:
                                        self.client_rds.delete_db_instance(
                                            DBInstanceIdentifier=subresource_id,
                                            SkipFinalSnapshot=True,
                                        )
                                except:
                                    self.logging.error(
                                        f"Could not delete RDS Cluster '{resource_id}' DB Instance '{subresource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.debug(
                                        f"RDS Cluster '{resource_id}' DB Instance '{subresource_id}' has been deleted."
                                    )

                            try:
                                if not self.is_dry_run:
                                    self.client_rds.delete_db_cluster(
                                        DBClusterIdentifier=resource_id,
                                        SkipFinalSnapshot=True,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete RDS Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"RDS Cluster '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Cluster '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"RDS Cluster '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "RDS",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of RDS Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of RDS Clusters.")
            return True

    def cluster_snapshots(self):
        """Deletes RDS Cluster Snapshots."""
        self.logging.debug("Started cleanup of RDS Cluster Snapshots.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.rds.cluster_snapshot.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.rds.cluster_snapshot.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "rds.cluster_snapshot"
        )

        if is_cleaning_enabled:
            try:
                paginator = self.client_rds.get_paginator(
                    "describe_db_cluster_snapshots"
                )
                resources = (
                    paginator.paginate(SnapshotType="manual")
                    .build_full_result()
                    .get("DBClusterSnapshots")
                )
            except:
                self.logging.error("Could not list all RDS Cluster Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("DBClusterSnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_rds.delete_db_cluster_snapshot(
                                    DBClusterSnapshotIdentifier=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete RDS Cluster Snapshot '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"RDS Cluster Snapshot '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"RDS Cluster Snapshot '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"RDS Cluster Snapshot '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "RDS",
                    "Cluster Snapshot",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of RDS Cluster Snapshots.")
            return True
        else:
            self.logging.debug("Skipping cleanup of RDS Cluster Snapshots.")
            return True

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
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.rds.instance.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "rds.instance")

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

                if not resource.get("DBClusterIdentifier"):
                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
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
                            f"RDS Instance '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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
        """Deletes RDS Snapshots."""
        self.logging.debug("Started cleanup of RDS Snapshots.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.rds.snapshot.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.rds.snapshot.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "rds.snapshot")

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

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
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
                        f"RDS Snapshot '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
