import sys

import boto3

from . import lambda_helper


class CloudFormationCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_cloudformation = None

    @property
    def client_cloudformation(self):
        if not self._client_cloudformation:
            self._client_cloudformation = boto3.client(
                "cloudformation", region_name=self.region
            )
        return self._client_cloudformation

    def run(self):
        self.stacks()

    def stacks(self):
        """
        Deletes CloudFormation Stacks.
        """

        clean = (
            self.settings.get("services", {})
            .get("cloudformation", {})
            .get("stacks", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_cloudformation.describe_stacks().get("Stacks")
            except:
                self.logging.error("Could not list all CloudFormation Stacks.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("cloudformation", {})
                .get("stacks", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("StackName")
                resource_date = (
                    resource.get("LastUpdatedTime")
                    if resource.get("LastUpdatedTime") is not None
                    else resource.get("CreationTime")
                )

                if resource_id not in self.whitelist.get("cloudformation", {}).get(
                    "stack", []
                ):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_cloudformation.delete_stack(
                                    StackName=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete CloudFormation Stack '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                        self.logging.info(
                            f"CloudFormation Stack '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"CloudFormation Stack '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"CloudFormation Stack '{resource_id}' has been whitelisted and has not "
                        "been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "CloudFormation", {}
                ).setdefault("Stacks", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of CloudFormation Stacks.")
            return True
