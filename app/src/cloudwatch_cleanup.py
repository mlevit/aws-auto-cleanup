import sys
import datetime

import boto3

from src.helper import Helper


class CloudWatchCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_logs = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_logs(self):
        if not self._client_logs:
            self._client_logs = boto3.client("logs", region_name=self.region)
        return self._client_logs

    def run(self):
        self.log_groups()

    def log_groups(self):
        """
        Deletes CloudWatch Log Groups.
        """

        self.logging.debug("Started cleanup of CloudWatch Log Groups.")

        clean = (
            self.settings.get("services", {})
            .get("cloudwatch", {})
            .get("log_group", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_logs.get_paginator("describe_log_groups")
                resources = paginator.paginate().build_full_result().get("logGroups")
            except:
                self.logging.error("Could not list all CloudWatch Log Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("cloudwatch", {})
                .get("log_group", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("logGroupName")
                resource_date = datetime.datetime.fromtimestamp(
                    resource.get("creationTime") / 1000.0
                ).strftime("%Y-%m-%d %H:%M:%S")
                resource_action = None

                if resource_id not in self.whitelist.get("cloudwatch", {}).get(
                    "log_group", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_logs.delete_log_group(
                                    logGroupName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete CloudWatch Log Group '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"CloudWatch Log Group '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"CloudWatch Log Group '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"CloudWatch Log Group '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "CloudWatch",
                    "Log Group",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of CloudWatch Log Groups.")
            return True
        else:
            self.logging.info("Skipping cleanup of CloudWatch Log Groups.")
            return True
