import sys
import datetime
import threading

import boto3

from src.helper import Helper


class CloudFormationCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_cloudformation = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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

        self.logging.debug("Started cleanup of CloudFormation Stacks.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.cloudformation.stack.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.cloudformation.stack.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(
            self.whitelist, "cloudformation.stack"
        )

        if is_cleaning_enabled:
            try:
                paginator = self.client_cloudformation.get_paginator("describe_stacks")
                resources = paginator.paginate().build_full_result().get("Stacks")
            except:
                self.logging.error("Could not list all CloudFormation Stacks.")
                self.logging.error(sys.exc_info()[1])
                return False

            # threads list
            threads = []

            for resource in resources:
                threads.append(
                    threading.Thread(
                        target=self.delete_stack,
                        args=(resource, resource_whitelist, maximum_resource_age),
                    )
                )

            # start all threads
            for thread in threads:
                thread.start()

            # make sure that all threads have finished
            for thread in threads:
                thread.join()

            self.logging.debug("Finished cleanup of CloudFormation Stacks.")
        else:
            self.logging.info("Skipping cleanup of CloudFormation Stacks.")
            return True

    def delete_stack(self, resource, resource_whitelist, maximum_resource_age):
        resource_id = resource.get("StackName")
        resource_date = resource.get("LastUpdatedTime", resource.get("CreationTime"))
        resource_status = resource.get("StackStatus")
        resource_protection = True  # resource.get("EnableTerminationProtection")
        resource_age = Helper.get_day_delta(resource_date).days
        resource_action = None

        if resource_id not in resource_whitelist:
            if resource_age > maximum_resource_age:
                # form a list of resources that cannot be delete
                retain_resources = []
                if resource_status in ("DELETE_FAILED"):
                    try:
                        paginator = self.client_cloudformation.get_paginator(
                            "list_stack_resources"
                        )
                        stack_resources = (
                            paginator.paginate(StackName=resource_id)
                            .build_full_result()
                            .get("StackResourceSummaries")
                        )
                    except:
                        self.logging.error(
                            f"Could not retrieve a list of Stack Resources for CloudFormation Stack '{resource_id}'."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        for stack_resource in stack_resources:
                            if stack_resource.get("ResourceStatus") in (
                                "DELETE_FAILED"
                            ) and stack_resource.get("ResourceType") in (
                                "AWS::S3::Bucket"
                            ):
                                retain_resources.append(
                                    stack_resource.get("LogicalResourceId")
                                )

                # remove termination protection
                if resource_protection:
                    try:
                        if not self.is_dry_run:
                            self.client_cloudformation.update_termination_protection(
                                EnableTerminationProtection=False,
                                StackName=resource_id,
                            )
                    except:
                        self.logging.error(
                            f"Could not disable Termination Protection for CloudFormation Stack '{resource_id}'."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        self.logging.debug(
                            f"Termination Protection for CloudFormation Stack '{resource_id}' disabled."
                        )

                try:
                    if not self.is_dry_run:
                        self.client_cloudformation.delete_stack(
                            StackName=resource_id,
                            RetainResources=retain_resources,
                        )
                except:
                    self.logging.error(
                        f"Could not delete CloudFormation Stack '{resource_id}'. "
                        "Manual deletion by an administrator might be necessary."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    try:
                        if not self.is_dry_run:
                            waiter = self.client_cloudformation.get_waiter(
                                "stack_delete_complete"
                            )
                            waiter.wait(
                                StackName=resource_id,
                                WaiterConfig={"Delay": 5, "MaxAttempts": 6},
                            )
                    except:
                        self.logging.warn(
                            f"Did not delete CloudFormation Stack '{resource_id}' within 30 seconds. "
                            "Stopped waiting, check progress manually."
                        )
                        self.logging.warn(sys.exc_info()[1])
                        resource_action = "DELETE - NOT CONFIRMED"
                    else:
                        self.logging.info(
                            f"CloudFormation Stack '{resource_id}' was last modified {resource_age} days ago "
                            "and has been deleted."
                        )
                        resource_action = "DELETE"
            else:
                self.logging.debug(
                    f"CloudFormation Stack '{resource_id}' was last modified {resource_age} days ago "
                    "(less than TTL setting) and has not been deleted."
                )
                resource_action = "SKIP - TTL"
        else:
            self.logging.debug(
                f"CloudFormation Stack '{resource_id}' has been whitelisted and has not "
                "been deleted."
            )
            resource_action = "SKIP - WHITELIST"

        # For CloudFormation Stacks that are not deleted, add all physical
        # resources into the Whitelist dictionary to prevent the need to whitelist
        # each and every resource
        if resource_action in ("SKIP - WHITELIST", "SKIP - TTL"):
            try:
                resource_details = self.client_cloudformation.describe_stack_resources(
                    StackName=resource_id
                ).get("StackResources")
            except:
                self.logging.error(
                    f"Could not Describe Stack Resources for CloudFormation Stack '{resource_id}'."
                )
                self.logging.error(sys.exc_info()[1])
            else:
                for stack_resource in resource_details:
                    resource_child_id = stack_resource.get("PhysicalResourceId")

                    try:
                        _, service, resource = stack_resource.get("ResourceType").split(
                            "::"
                        )
                    except:
                        self.logging.warn(
                            f"""CloudFormation Stack '{resource_id}' resource '{stack_resource.get("ResourceType")}' """
                            """does not conform to the standard 'service-provider::service-name::data-type-name' and cannot be whitelisted."""
                        )
                    else:
                        self.whitelist[service.lower()][resource.lower()].add(
                            resource_child_id
                        )

                        self.logging.debug(
                            f"{service} {resource} '{resource_child_id}' has been added to the whitelist."
                        )

        Helper.record_execution_log_action(
            self.execution_log,
            self.region,
            "CloudFormation",
            "Stack",
            resource_id,
            resource_action,
        )

        return True
