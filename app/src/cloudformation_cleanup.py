import sys
import threading

import boto3

from src.helper import Helper


class CloudFormationCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_cloudformation = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

        self.resource_translations = {"ManagedPolicy": "Policy"}

    @property
    def client_cloudformation(self):
        if not self._client_cloudformation:
            self._client_cloudformation = boto3.client(
                "cloudformation", region_name=self.region
            )
        return self._client_cloudformation

    def get_stack_name(self, stack_id):
        if stack_id:
            try:
                paginator = self.client_cloudformation.get_paginator("describe_stacks")
                resources = (
                    paginator.paginate(StackName=stack_id)
                    .build_full_result()
                    .get("Stacks")
                )
            except:
                self.logging.error(
                    f"Could not describe CloudFormation Stack '{stack_id}'."
                )
                self.logging.error(sys.exc_info()[1])
            else:
                for resource in resources:
                    return resource["StackName"]

        return None

    def run(self):
        self.stacks()

    def stacks(self):
        """Deletes CloudFormation Stacks."""
        self.logging.debug("Started cleanup of CloudFormation Stacks.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.cloudformation.stack.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.cloudformation.stack.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "cloudformation.stack"
        )
        semaphore = threading.Semaphore(value=1)

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
                        args=(
                            semaphore,
                            resource,
                            resource_allowlist,
                            resource_maximum_age,
                        ),
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

    def delete_stack(
        self, semaphore, resource, resource_allowlist, resource_maximum_age
    ):
        semaphore.acquire()

        resource_id = resource.get("StackName")
        resource_date = resource.get("LastUpdatedTime", resource.get("CreationTime"))
        resource_status = resource.get("StackStatus")
        resource_protection = True  # resource.get("EnableTerminationProtection")
        resource_parent_stack_id = self.get_stack_name(resource.get("ParentId"))
        resource_root_stack_id = self.get_stack_name(resource.get("RootId"))
        resource_age = Helper.get_day_delta(resource_date).days
        resource_action = None

        if (
            Helper.not_allowlisted(resource_id, resource_allowlist)
            and resource_parent_stack_id not in resource_allowlist
            and resource_root_stack_id not in resource_allowlist
        ):
            if resource_age > resource_maximum_age:
                if resource_status not in (
                    "DELETE_PENDING",
                    "DELETE_IN_PROGRESS",
                    "DELETE_COMPLETE",
                ):
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
                    if resource_protection and resource_root_stack_id is None:
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
                        self.logging.info(
                            f"CloudFormation Stack '{resource_id}' was last modified {resource_age} days ago "
                            "and has started being deleted. Check progress manually."
                        )
                        resource_action = "DELETE - NOT CONFIRMED"
            else:
                self.logging.debug(
                    f"CloudFormation Stack '{resource_id}' was last modified {resource_age} days ago "
                    "(less than TTL setting) and has not been deleted."
                )
                resource_action = "SKIP - TTL"
        else:
            if resource_id in resource_allowlist:
                self.logging.debug(
                    f"CloudFormation Stack '{resource_id}' has been allowlisted and has not "
                    "been deleted."
                )
            elif resource_parent_stack_id in resource_allowlist:
                self.logging.debug(
                    f"CloudFormation Stack's '{resource_id}' parent CloudFormation Stack '{resource_parent_stack_id}' "
                    "has been allowlisted and has not been deleted."
                )
            elif resource_root_stack_id in resource_allowlist:
                self.logging.debug(
                    f"CloudFormation Stack's '{resource_id}' root CloudFormation Stack '{resource_root_stack_id}' "
                    "has been allowlisted and has not been deleted."
                )

            resource_action = "SKIP - ALLOWLIST"

        # For CloudFormation Stacks that are not deleted, add all physical
        # resources into the Allowlist dictionary to prevent the need to allowlist
        # each and every resource
        if resource_action in ("SKIP - ALLOWLIST", "SKIP - TTL"):
            try:
                resource_details = self.client_cloudformation.describe_stack_resources(
                    StackName=resource_id
                ).get("StackResources")
            except:
                self.logging.error(
                    f"Could not Describe Stack Resources for CloudFormation Stack '{resource_id}'."
                )
                self.logging.error(sys.exc_info()[1])
                resource_action = "ERROR"
            else:
                for stack_resource in resource_details:
                    resource_child_logical_id = stack_resource.get("LogicalResourceId")
                    resource_child_physical_id = stack_resource.get(
                        "PhysicalResourceId"
                    )
                    resource_type = stack_resource.get("ResourceType")

                    try:
                        _, service, resource = resource_type.split("::")
                    except:
                        self.logging.debug(
                            f"CloudFormation Stack '{resource_id}' resource '{resource_type}' "
                            "does not conform to the standard 'service-provider::service-name::data-type-name' and cannot be allowlisted."
                        )
                    else:
                        if resource_child_physical_id not in (None, ""):
                            # Some resources are coming through as full ARNs instead of just
                            # resource ID. Strip the ARN to just the resource ID.
                            if "/" in resource_child_physical_id:
                                resource_child_physical_id = (
                                    resource_child_physical_id.split("/")[1]
                                )

                            if resource in self.resource_translations:
                                resource = self.resource_translations[resource]

                            self.allowlist[service.lower()][resource.lower()].add(
                                resource_child_physical_id
                            )

                            self.logging.debug(
                                f"{service} {resource} '{resource_child_physical_id}' has been added to the allowlist."
                            )
                        else:
                            self.logging.debug(
                                f"CloudFormation Stack '{resource_id}' resource '{resource_child_logical_id}' "
                                "does not have a PhysicalResourceId and cannot be allowlisted."
                            )

        Helper.record_execution_log_action(
            self.execution_log,
            self.region,
            "CloudFormation",
            "Stack",
            resource_id,
            resource_action,
        )

        semaphore.release()

        return True
