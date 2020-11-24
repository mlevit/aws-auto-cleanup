import sys
import datetime

import boto3

from src.helper import Helper


class KafkaCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_kafka = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_kafka(self):
        if not self._client_kafka:
            self._client_kafka = boto3.client("kafka", region_name=self.region)
        return self._client_kafka

    def run(self):
        self.clusters()

    def clusters(self):
        """
        Deletes Kafka Clusters.
        """

        self.logging.debug("Started cleanup of Kafka Clusters.")

        clean = (
            self.settings.get("services", {})
            .get("kafka", {})
            .get("cluster", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_kafka.list_clusters().get("ClusterInfoList")
            except:
                self.logging.error("Could not list all Kafka Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("kafka", {})
                .get("cluster", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ClusterName")
                resource_arn = resource.get("ClusterArn")
                resource_date = resource.get("CreationTime")
                resource_action = None

                if resource_id not in self.whitelist.get("kafka", {}).get(
                    "cluster", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
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
                                f"Kafka Cluster '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Kafka Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Kafka Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

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
