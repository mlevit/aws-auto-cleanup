import sys
import datetime

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
                resource_action = "skip"

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
                                resource_action = "error"
                                continue

                        self.logging.info(
                            f"CloudFormation Stack '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"CloudFormation Stack '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"CloudFormation Stack '{resource_id}' has been whitelisted and has not "
                        "been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "CloudFormation", {}
                ).setdefault("Stack", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

                # For CloudFormation Stacks that are not deleted, add all physical
                # resources into the Whitelist dictionary to prevent the need to whitelist
                # each and every resource
                if resource_action != "delete":
                    try:
                        resource_details = self.client_cloudformation.describe_stack_resources(
                            StackName=resource_id
                        ).get(
                            "StackResources"
                        )
                    except:
                        self.logging.error("Could not Describe Stack Resources.")
                        self.logging.error(sys.exc_info()[1])
                        return False

                    for _ in resource_details:
                        id = _.get("PhysicalResourceId")
                        platform, service, resource = _.get("ResourceType").split("::")

                        self.whitelist.setdefault(service.lower(), {}).setdefault(
                            resource.lower(), set()
                        ).add(id)

                        self.logging.debug(
                            f"{service} {resource} has been added to the Whitelist."
                        )
            return True
        else:
            self.logging.info("Skipping cleanup of CloudFormation Stacks.")
            return True
