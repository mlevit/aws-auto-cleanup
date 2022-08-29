import sys

import boto3

from src.helper import Helper


class KafkaCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_kafka = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_kafka(self):
        if not self._client_kafka:
            self._client_kafka = boto3.client("kafka", region_name=self.region)
        return self._client_kafka

    def run(self):
        self.clusters()

    def clusters(self):
        """Deletes Kafka Clusters."""
        self.logging.debug("Started cleanup of Kafka Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.kafka.cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.kafka.cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "kafka.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_kafka.get_paginator("list_clusters_v2")
                resources = (
                    paginator.paginate().build_full_result().get("ClusterInfoList")
                )
            except:
                self.logging.error("Could not list all Kafka Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ClusterName")
                resource_arn = resource.get("ClusterArn")
                resource_date = resource.get("CreationTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_kafka.delete_cluster(
                                    ClusterArn=resource_arn
                                )
                        except:
                            self.logging.error(
                                f"Could not delete Kafka Cluster '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Kafka Cluster '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Kafka Cluster '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Kafka Cluster '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Kafka",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Kafka Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of Kafka Clusters.")
            return True
