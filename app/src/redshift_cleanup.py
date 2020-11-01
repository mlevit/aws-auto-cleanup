import sys
import datetime

import boto3

from src.helper import Helper


class RedshiftCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_redshift = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_redshift(self):
        if not self._client_redshift:
            self._client_redshift = boto3.client("redshift", region_name=self.region)
        return self._client_redshift

    def run(self):
        self.clusters()
        self.snapshots()

    def clusters(self):
        """
        Deletes Redshift Clusters.
        """

        self.logging.debug("Started cleanup of Redshift Clusters.")

        clean = (
            self.settings.get("services", {})
            .get("redshift", {})
            .get("cluster", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_redshift.describe_clusters().get("Clusters")
            except:
                self.logging.error("Could not list all Redshift Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("redshift", {})
                .get("cluster", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ClusterIdentifier")
                resource_date = resource.get("ClusterCreateTime")
                resource_status = resource.get("ClusterStatus")
                resource_action = None

                if resource_id not in self.whitelist.get("redshift", {}).get(
                    "cluster", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status == "available":
                            try:
                                if not self._dry_run:
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
                                    f"Redshift Cluster '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.warn(
                                f"Redshift Cluster '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                    else:
                        self.logging.debug(
                            f"Redshift Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Redshift Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "Redshift", {}
                ).setdefault("Cluster", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of Redshift Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Clusters.")
            return True

    def snapshots(self):
        """
        Deletes Redshift Snapshots.
        """

        self.logging.debug("Started cleanup of Redshift Snapshots.")

        clean = (
            self.settings.get("services", {})
            .get("redshift", {})
            .get("snapshot", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_redshift.describe_cluster_snapshots(
                    SnapshotType="manual",
                ).get("Snapshots")
            except:
                self.logging.error("Could not list all Redshift Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("redshift", {})
                .get("snapshot", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("SnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_status = resource.get("Status")
                resource_action = None

                if resource_id not in self.whitelist.get("redshift", {}).get(
                    "snapshot", []
                ):
                    delta = Helper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if resource_status in ("available", "final snapshot"):
                            try:
                                if not self._dry_run:
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
                                    f"Redshift Snapshot '{resource_id}' was created {delta.days} days ago "
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
                            f"Redshift Snapshot '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Redshift Snapshot '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "Redshift", {}
                ).setdefault("Snapshot", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of Redshift Snapshots.")
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Snapshots.")
            return True
