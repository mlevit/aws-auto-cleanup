import sys

import boto3

from src.helper import Helper


class KinesisCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
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
        """
        Deletes Kinesis Streams.
        """

        self.logging.debug("Started cleanup of Kinesis Streams.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.kinesis.stream.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.kinesis.stream.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "kinesis.stream")

        if is_cleaning_enabled:
            try:
                paginator = self.client_kinesis.get_paginator("list_streams")
                resources = paginator.paginate().build_full_result()["StreamNames"]
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
                    )["StreamDescription"]
                except:
                    self.logging.error(
                        f"Could not get Kinesis Stream's '{resource_id}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_status = resource_details["StreamStatus"]
                    resource_date = resource_details["StreamCreationTimestamp"]
                    resource_age = Helper.get_day_delta(resource_date).days

                    if resource_id not in resource_whitelist:

                        if resource_age > maximum_resource_age:
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
                            f"Kinesis Stream '{resource_id}' has been whitelisted and has not been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

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
