import sys

import boto3

from src.helper import Helper


class RedshiftCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_redshift = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_redshift(self):
        if not self._client_redshift:
            self._client_redshift = boto3.client("redshift", region_name=self.region)
        return self._client_redshift

    def run(self):
        self.clusters()
        self.snapshots()

    def clusters(self):
        """Deletes Redshift Clusters."""
        self.logging.debug("Started cleanup of Redshift Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.redshift.cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.redshift.cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "redshift.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_redshift.get_paginator("describe_clusters")
                resources = paginator.paginate().build_full_result().get("Clusters")
            except:
                self.logging.error("Could not list all Redshift Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ClusterIdentifier")
                resource_date = resource.get("ClusterCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_redshift.delete_cluster(
                                    ClusterIdentifier=resource_id,
                                    SkipFinalClusterSnapshot=True,
                                )
                        except:
                            self.logging.error(
                                f"Could not delete Redshift Cluster '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Redshift Cluster '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Redshift Cluster '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Redshift Cluster '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Redshift",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Redshift Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Clusters.")
            return True

    def snapshots(self):
        """Deletes Redshift Snapshots."""
        self.logging.debug("Started cleanup of Redshift Snapshots.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.redshift.snapshot.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.redshift.snapshot.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "redshift.snapshot")

        if is_cleaning_enabled:
            try:
                paginator = self.client_redshift.get_paginator(
                    "describe_cluster_snapshots"
                )
                resources = (
                    paginator.paginate(SnapshotType="manual")
                    .build_full_result()
                    .get("Snapshots")
                )
            except:
                self.logging.error("Could not list all Redshift Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("SnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_status = resource.get("Status")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_status in ("available", "final snapshot"):
                            try:
                                if not self.is_dry_run:
                                    self.client_redshift.delete_cluster_snapshot(
                                        SnapshotIdentifier=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete Redshift Snapshot '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Redshift Snapshot '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.warn(
                                f"Redshift Snapshot '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                    else:
                        self.logging.debug(
                            f"Redshift Snapshot '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Redshift Snapshot '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Redshift",
                    "Snapshot",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Redshift Snapshots.")
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Snapshots.")
            return True
