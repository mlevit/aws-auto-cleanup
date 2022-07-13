import sys

import boto3

from src.helper import Helper


class KinesisCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_kinesis = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_kinesis(self):
        if not self._client_kinesis:
            self._client_kinesis = boto3.client("kinesis", region_name=self.region)
        return self._client_kinesis

    def run(self):
        self.streams()

    def streams(self):
        """Deletes Kinesis Streams."""
        self.logging.debug("Started cleanup of Kinesis Streams.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.kinesis.stream.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.kinesis.stream.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "kinesis.stream")

        if is_cleaning_enabled:
            try:
                paginator = self.client_kinesis.get_paginator("list_streams")
                resources = paginator.paginate().build_full_result().get("StreamNames")
            except:
                self.logging.error("Could not list all Kinesis Streams.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource
                resource_action = None

                try:
                    resource_details = self.client_kinesis.describe_stream(
                        StreamName=resource_id
                    ).get("StreamDescription")
                except:
                    self.logging.error(
                        f"Could not get Kinesis Stream's '{resource_id}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_status = resource_details.get("StreamStatus")
                    resource_date = resource_details.get("StreamCreationTimestamp")
                    resource_age = Helper.get_day_delta(resource_date).days

                    if Helper.not_allowlisted(resource_id, resource_allowlist):

                        if resource_age > resource_maximum_age:
                            if resource_status == "ACTIVE":
                                try:
                                    if not self.is_dry_run:
                                        self.client_kinesis.delete_stream(
                                            StreamName=resource_id,
                                            EnforceConsumerDeletion=True,
                                        )
                                except:
                                    self.logging.error(
                                        f"Could not delete Kinesis Stream '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.info(
                                        f"Kinesis Stream '{resource_id}' was created {resource_age} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "DELETE"
                            else:
                                self.logging.warn(
                                    f"Kinesis Stream '{resource_id}' in state '{resource_status}' cannot be deleted."
                                )
                                resource_action = "SKIP - IN USE"
                        else:
                            self.logging.debug(
                                f"Kinesis Stream '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Kinesis Stream '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Kinesis",
                    "Stream",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Kinesis Streams.")
            return True
        else:
            self.logging.info("Skipping cleanup of Kinesis Streams.")
            return True
