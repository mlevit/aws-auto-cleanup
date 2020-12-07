import sys

import boto3

from src.helper import Helper


class LambdaCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_lambda = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_lambda(self):
        if not self._client_lambda:
            self._client_lambda = boto3.client("lambda", region_name=self.region)
        return self._client_lambda

    def run(self):
        self.functions()

    def functions(self):
        """
        Deletes Lambda Functions.
        """

        self.logging.debug("Started cleanup of Lambda Functions.")

        clean = (
            self.settings.get("services", {})
            .get("lambda", {})
            .get("function", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_lambda.get_paginator("list_functions")
                resources = paginator.paginate().build_full_result().get("Functions")
            except:
                self.logging.error("Could not list all Lambda Functions.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("lambda", {})
                .get("function", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("FunctionName")
                resource_date = resource.get("LastModified")
                resource_action = None

                if resource_id not in self.whitelist.get("lambda", {}).get(
                    "function", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_lambda.delete_function(
                                    FunctionName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete Lambda Function '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Lambda Function '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Lambda Function '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Lambda Function '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Lambda",
                    "Function",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Lambda Functions.")
            return True
        else:
            self.logging.info("Skipping cleanup of Lambda Functions.")
            return True
