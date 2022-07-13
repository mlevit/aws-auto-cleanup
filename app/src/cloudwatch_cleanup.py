import sys
import datetime

import boto3

from src.helper import Helper


class CloudWatchCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_logs = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_logs(self):
        if not self._client_logs:
            self._client_logs = boto3.client("logs", region_name=self.region)
        return self._client_logs

    def run(self):
        self.log_groups()

    def log_groups(self):
        """Deletes CloudWatch Log Groups."""
        self.logging.debug("Started cleanup of CloudWatch Log Groups.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.cloudwatch.log_group.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.cloudwatch.log_group.ttl", 30
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "cloudwatch.log_group"
        )

        if is_cleaning_enabled:
            try:
                paginator = self.client_logs.get_paginator("describe_log_groups")
                resources = paginator.paginate().build_full_result().get("logGroups")
            except:
                self.logging.error("Could not list all CloudWatch Log Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("logGroupName")
                resource_date = datetime.datetime.fromtimestamp(
                    resource.get("creationTime") / 1000.0
                ).strftime("%Y-%m-%d %H:%M:%S")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
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
                                f"CloudWatch Log Group '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"CloudWatch Log Group '{resource_id}' was created {resource_age} days ago (less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"CloudWatch Log Group '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
