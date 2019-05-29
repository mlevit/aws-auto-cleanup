import sys

import boto3

from . import lambda_helper


class DynamoDBCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
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

        clean = (
            self.settings.get("services", {})
            .get("dynamodb", {})
            .get("tables", {})
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
                .get("tables", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_date = (
                    self.client_dynamodb.describe_table(TableName=resource)
                    .get("Table")
                    .get("CreationDateTime")
                )

                if resource not in self.whitelist.get("dynamodb", {}).get("table", []):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_dynamodb.delete_table(TableName=resource)
                            except:
                                self.logging.error(
                                    f"Could not delete DynamoDB Table '{resource}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                        self.logging.info(
                            f"DynamoDB Table '{resource}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"DynamoDB Table '{resource}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"DynamoDB Table '{resource}' has been whitelisted and has not "
                        "been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "DynamoDB", {}
                ).setdefault("Tables", []).append(resource)
            return True
        else:
            self.logging.info("Skipping cleanup of DynamoDB Tables.")
            return True
