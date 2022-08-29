import sys

import boto3

from src.helper import Helper


class ELBCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elb = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_elb(self):
        if not self._client_elb:
            self._client_elb = boto3.client("elbv2", region_name=self.region)
        return self._client_elb

    def run(self):
        self.load_balancers()

    def load_balancers(self):
        """Deletes ELB Load Balancers."""
        self.logging.debug("Started cleanup of ELB Load Balancers.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.elb.load_balancer.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.elb.load_balancer.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "elb.load_balancer")

        if is_cleaning_enabled:
            try:
                paginator = self.client_elb.get_paginator("describe_load_balancers")
                resources = (
                    paginator.paginate().build_full_result().get("LoadBalancers")
                )
            except:
                self.logging.error("Could not list all ELB Load Balancers.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("LoadBalancerName")
                resource_arn = resource.get("LoadBalancerArn")
                resource_date = resource.get("CreatedTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_elb.modify_load_balancer_attributes(
                                    LoadBalancerArn=resource_arn,
                                    Attributes=[
                                        {
                                            "Key": "deletion_protection.enabled",
                                            "Value": "false",
                                        },
                                    ],
                                )
                        except:
                            self.logging.error(
                                f"Could not disable Delete Protection for ELB Load Balancer '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            try:
                                if not self.is_dry_run:
                                    self.client_elb.delete_load_balancer(
                                        LoadBalancerArn=resource_arn
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete ELB Load Balancer '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"ELB Load Balancer '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ELB Load Balancer '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"ELB Load Balancer '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ELB",
                    "Load Balancer",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of ELB Load Balancers.")
            return True
        else:
            self.logging.info("Skipping cleanup of ELB Load Balancers.")
            return True
