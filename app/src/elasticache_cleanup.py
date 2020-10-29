import sys
import datetime

import boto3

from src.helper import Helper


class ElastiCacheCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticache = None

    @property
    def client_elasticache(self):
        if not self._client_elasticache:
            self._client_elasticache = boto3.client(
                "elasticache", region_name=self.region
            )
        return self._client_elasticache

    def run(self):
        self.clusters()
        self.replication_groups()

    def clusters(self):
        """
        Deletes ElastiCache Clusters.
        """

        self.logging.debug("Started cleanup of ElastiCache Clusters.")

        clean = (
            self.settings.get("services", {})
            .get("elasticache", {})
            .get("cluster", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_elasticache.describe_cache_clusters(
                    ShowCacheClustersNotInReplicationGroups=True
                ).get("CacheClusters")
            except:
                self.logging.error("Could not list all ElastiCache Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("elasticache", {})
                .get("cluster", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("CacheClusterId")
                resource_date = resource.get("CacheClusterCreateTime")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("elasticache", {}).get(
                    "cluster", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_elasticache.delete_cache_cluster(
                                    CacheClusterId=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete ElastiCache Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "error"
                                continue

                        self.logging.info(
                            f"ElastiCache Cluster '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"ElastiCache Cluster '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"ElastiCache Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "ElastiCache", {}
                ).setdefault("Cluster", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of ElastiCache Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of ElastiCache Clusters.")
            return True

    def replication_groups(self):
        """
        Deletes ElastiCache Replication Groups.
        """

        self.logging.debug("Started cleanup of ElastiCache Replication Groups.")

        clean = (
            self.settings.get("services", {})
            .get("elasticache", {})
            .get("replication_group", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_elasticache.describe_replication_groups().get(
                    "ReplicationGroups"
                )
            except:
                self.logging.error("Could not list all ElastiCache Replication Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("elasticache", {})
                .get("replication_group", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ReplicationGroupId")
                resource_primary_cluster_id = resource.get("MemberClusters")[0]

                try:
                    resource_primary_cluster_details = (
                        self.client_elasticache.describe_cache_clusters(
                            CacheClusterId=resource_primary_cluster_id
                        ).get("CacheClusters")[0]
                    )
                except:
                    self.logging.error(
                        f"Could not describe ElastiCache Cluster '{resource_primary_cluster_id}'."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "error"
                    continue

                resource_date = resource_primary_cluster_details.get(
                    "CacheClusterCreateTime"
                )
                resource_action = "skip"

                if resource_id not in self.whitelist.get("elasticache", {}).get(
                    "replication_group", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_elasticache.delete_replication_group(
                                    ReplicationGroupId=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete ElastiCache Replication Group '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "error"
                                continue

                        self.logging.info(
                            f"ElastiCache Replication Group '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"ElastiCache Replication Group '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"ElastiCache Replication Group '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "ElastiCache", {}
                ).setdefault("Replication Group", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of ElastiCache Replication Groups.")
            return True
        else:
            self.logging.info("Skipping cleanup of ElastiCache Replication Groups.")
            return True