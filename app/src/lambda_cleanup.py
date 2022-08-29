import sys

import boto3

from src.helper import Helper


class LambdaCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_lambda = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_lambda(self):
        if not self._client_lambda:
            self._client_lambda = boto3.client("lambda", region_name=self.region)
        return self._client_lambda

    def run(self):
        self.functions()

    def functions(self):
        """Deletes Lambda Functions."""
        self.logging.debug("Started cleanup of Lambda Functions.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.lambda.function.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.lambda.function.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "lambda.function")

        if is_cleaning_enabled:
            try:
                paginator = self.client_lambda.get_paginator("list_functions")
                resources = paginator.paginate().build_full_result().get("Functions")
            except:
                self.logging.error("Could not list all Lambda Functions.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("FunctionName")
                resource_date = resource.get("LastModified")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
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
                                f"Lambda Function '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Lambda Function '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Lambda Function '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
