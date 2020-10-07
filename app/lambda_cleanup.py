import sys
import datetime

import boto3

import helper


class LambdaCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_lambda = None

    @property
    def client_lambda(self):
        if not self._client_lambda:
            self._client_lambda = boto3.client("lambda", region_name=self.region)
        return self._client_lambda

    def run(self):
        self.functions()
        self.layers()

    def functions(self):
        """
        Deletes Lambda Functions.
        """

        clean = (
            self.settings.get("services", {})
            .get("lambda", {})
            .get("function", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_lambda.list_functions().get("Functions")
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
                resource_action = "skip"

                if resource_id not in self.whitelist.get("lambda", {}).get(
                    "function", []
                ):
                    delta = helper.Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_lambda.delete_function(
                                    FunctionName=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete Lambda Function '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "error"
                                continue

                        self.logging.info(
                            f"Lambda Function '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"Lambda Function '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"Lambda Function '%s' has been whitelisted and has not been deleted."
                        % (resource_id)
                    )
                    resource_action = "skip - whitelist"

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "Lambda", {}
                ).setdefault("Function", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )
            return True
        else:
            self.logging.info("Skipping cleanup of Lambda Functions.")
            return True

    def layers(self):
        pass
