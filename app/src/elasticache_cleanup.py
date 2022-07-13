import sys

import boto3

from src.helper import Helper


class ElastiCacheCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticache = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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
        """Deletes ElastiCache Clusters."""
        self.logging.debug("Started cleanup of ElastiCache Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.elasticache.cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.elasticache.cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "elasticache.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_elasticache.get_paginator(
                    "describe_cache_clusters"
                )
                resources = (
                    paginator.paginate(ShowCacheClustersNotInReplicationGroups=True)
                    .build_full_result()
                    .get("CacheClusters")
                )
            except:
                self.logging.error("Could not list all ElastiCache Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("CacheClusterId")
                resource_date = resource.get("CacheClusterCreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_elasticache.delete_cache_cluster(
                                    CacheClusterId=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete ElastiCache Cluster '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"ElastiCache Cluster '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ElastiCache Cluster '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"ElastiCache Cluster '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ElastiCache",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of ElastiCache Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of ElastiCache Clusters.")
            return True

    def replication_groups(self):
        """Deletes ElastiCache Replication Groups."""
        self.logging.debug("Started cleanup of ElastiCache Replication Groups.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.elasticache.replication_group.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.elasticache.replication_group.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "elasticache.replication_group"
        )

        if is_cleaning_enabled:
            try:
                resources = self.client_elasticache.describe_replication_groups().get(
                    "ReplicationGroups"
                )
            except:
                self.logging.error("Could not list all ElastiCache Replication Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

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
                    resource_action = "ERROR"
                else:
                    resource_date = resource_primary_cluster_details.get(
                        "CacheClusterCreateTime"
                    )
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_elasticache.delete_replication_group(
                                        ReplicationGroupId=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete ElastiCache Replication Group '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"ElastiCache Replication Group '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"ElastiCache Replication Group '{resource_id}' was last modified {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"ElastiCache Replication Group '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ElastiCache",
                    "Replication Group",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of ElastiCache Replication Groups.")
            return True
        else:
            self.logging.info("Skipping cleanup of ElastiCache Replication Groups.")
            return True
