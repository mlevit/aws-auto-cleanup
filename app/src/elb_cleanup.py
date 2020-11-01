import sys
import datetime

import boto3

from src.helper import Helper


class ELBCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elb = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_elb(self):
        if not self._client_elb:
            self._client_elb = boto3.client("elb", region_name=self.region)
        return self._client_elb

    def run(self):
        self.load_balancers()

    def load_balancers(self):
        """
        Deletes ELB Load Balancers.
        """

        self.logging.debug("Started cleanup of ELB Load Balancers.")

        clean = (
            self.settings.get("services", {})
            .get("elb", {})
            .get("load_balancer", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_elb.describe_load_balancers().get(
                    "LoadBalancerDescriptions"
                )
            except:
                self.logging.error("Could not list all ELB Load Balancers.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("elb", {})
                .get("load_balancer", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("LoadBalancerName")
                resource_date = resource.get("CreatedTime")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("elb", {}).get(
                    "load_balancer", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_elb.delete_load_balancer(
                                    LoadBalancerName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete ELB Load Balancer '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"ELB Load Balancer '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ELB Load Balancer '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"ELB Load Balancer '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "ELB", {}
                ).setdefault("Load Balancer", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of ELB Load Balancers.")
            return True
        else:
            self.logging.info("Skipping cleanup of ELB Load Balancers.")
            return True
