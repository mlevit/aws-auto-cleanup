import sys

import boto3

from src.helper import Helper


class DynamoDBCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_dax = None
        self._client_dynamodb = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_dax(self):
        if not self._client_dax:
            self._client_dax = boto3.client("dax", region_name=self.region)
        return self._client_dax

    @property
    def client_dynamodb(self):
        if not self._client_dynamodb:
            self._client_dynamodb = boto3.client("dynamodb", region_name=self.region)
        return self._client_dynamodb

    def run(self):
        self.dax_clusters()
        self.tables()

    def dax_clusters(self):
        """
        Deletes DynamoDB DAX Clusters.
        """

        self.logging.debug("Started cleanup of DynamoDB DAX Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.dynamodb.dax_cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.dynamodb.dax_cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "dynamodb.dax_cluster"
        )

        if is_cleaning_enabled:
            try:
                paginator = self.client_dax.get_paginator("describe_clusters")
                resources = paginator.paginate().build_full_result().get("Clusters")
            except:
                self.logging.error("Could not list all DynamoDB DAX Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ClusterName")

                resource_date = None
                for node in resource.get("Nodes"):
                    if not resource_date or node.get("NodeCreateTime") < resource_date:
                        resource_date = node.get("NodeCreateTime")

                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_id not in resource_allowlist:
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_dynamodb.delete_cluster(
                                    ClusterName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete DynamoDB DAX Cluster '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"DynamoDB DAX Cluster '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"DynamoDB DAX Cluster '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"DynamoDB DAX Cluster '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "DynamoDB",
                    "DAX Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of DynamoDB DAX Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of DynamoDB DAX Clusters.")
            return True

    def tables(self):
        """
        Deletes DynamoDB Tables.
        """

        self.logging.debug("Started cleanup of DynamoDB Tables.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.dynamodb.table.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.dynamodb.table.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "dynamodb.table")

        if is_cleaning_enabled:
            try:
                paginator = self.client_dynamodb.get_paginator("list_tables")
                resources = paginator.paginate().build_full_result().get("TableNames")
            except:
                self.logging.error("Could not list all DynamoDB Tables.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                try:
                    resource_details = self.client_dynamodb.describe_table(
                        TableName=resource
                    ).get("Table")
                except:
                    self.logging.error(
                        f"Could not get DynamoDB Table's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_date = resource_details.get("CreationDateTime")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if resource not in resource_allowlist:
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_dynamodb.delete_table(
                                        TableName=resource
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete DynamoDB Table '{resource}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"DynamoDB Table '{resource}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"DynamoDB Table '{resource}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"DynamoDB Table '{resource}' has been allowlisted and has not "
                            "been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "DynamoDB",
                    "Table",
                    resource,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of DynamoDB Tables.")
            return True
        else:
            self.logging.info("Skipping cleanup of DynamoDB Tables.")
            return True
