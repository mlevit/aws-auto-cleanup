import sys

import boto3

from . import lambda_helper


class RedshiftCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_redshift = None

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

        clean = (
            self.settings.get("services", {})
            .get("redshift", {})
            .get("clusters", {})
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
                .get("clusters", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ClusterIdentifier")
                resource_date = resource.get("ClusterCreateTime")
                resource_status = resource.get("ClusterStatus")

                if resource_id not in self.whitelist.get("redshift", {}).get(
                    "cluster", []
                ):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status == "available":
                            if not self.settings.get("general", {}).get(
                                "dry_run", True
                            ):
                                try:
                                    self.client_redshift.delete_cluster(
                                        ClusterIdentifier=resource_id,
                                        SkipFinalClusterSnapshot=True,
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete Redshift Cluster '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    continue

                            self.logging.info(
                                f"Redshift Cluster '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                        else:
                            self.logging.debug(
                                f"Redshift Cluster '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                    else:
                        self.logging.debug(
                            f"Redshift Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"Redshift Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "Redshift", {}
                ).setdefault("Clusters", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Clusters.")
            return True

    def snapshots(self):
        """
        Deletes Redshift Snapshots.
        """

        clean = (
            self.settings.get("services", {})
            .get("redshift", {})
            .get("snapshots", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_redshift.describe_cluster_snapshots().get(
                    "Snapshots"
                )
            except:
                self.logging.error("Could not list all Redshift Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("redshift", {})
                .get("snapshots", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("SnapshotIdentifier")
                resource_date = resource.get("SnapshotCreateTime")
                resource_status = resource.get("Status")

                if resource_id not in self.whitelist.get("redshift", {}).get(
                    "snapshot", []
                ):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if resource_status in ("available", "final snapshot"):
                            if not self.settings.get("general", {}).get(
                                "dry_run", True
                            ):
                                try:
                                    self.client_redshift.delete_cluster_snapshot(
                                        SnapshotIdentifier=resource_id
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete Redshift Snapshot '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    continue

                            self.logging.info(
                                f"Redshift Snapshot '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                        else:
                            print("dry run")
                            self.logging.debug(
                                f"Redshift Snapshot '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                    else:
                        self.logging.debug(
                            f"Redshift Snapshot '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"Redshift Snapshot '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "Redshift", {}
                ).setdefault("Snapshots", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of Redshift Snapshots.")
            return True
