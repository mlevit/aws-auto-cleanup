import sys
import datetime

import boto3

from src.helper import Helper


class DynamoDBCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_dynamodb = None

    @property
    def client_dynamodb(self):
        if not self._client_dynamodb:
            self._client_dynamodb = boto3.client("dynamodb", region_name=self.region)
        return self._client_dynamodb

    def run(self):
        self.tables()

    def tables(self):
        """
        Deletes DynamoDB Tables.
        """

        self.logging.debug("Started cleanup of DynamoDB Tables.")

        clean = (
            self.settings.get("services", {})
            .get("dynamodb", {})
            .get("table", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_dynamodb.list_tables().get("TableNames")
            except:
                self.logging.error("Could not list all DynamoDB Tables.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("dynamodb", {})
                .get("table", {})
                .get("ttl", 7)
            )

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
                    resource_action = "error"
                    continue

                resource_date = resource_details.get("CreationDateTime")
                resource_action = "skip"

                if resource not in self.whitelist.get("dynamodb", {}).get("table", []):
                    delta = Helper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_dynamodb.delete_table(TableName=resource)
                            except:
                                self.logging.error(
                                    f"Could not delete DynamoDB Table '{resource}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "error"
                                continue

                        self.logging.info(
                            f"DynamoDB Table '{resource}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"DynamoDB Table '{resource}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"DynamoDB Table '{resource}' has been whitelisted and has not "
                        "been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "DynamoDB", {}
                ).setdefault("Table", []).append(
                    {
                        "id": resource,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of DynamoDB Tables.")
            return True
        else:
            self.logging.info("Skipping cleanup of DynamoDB Tables.")
            return True
