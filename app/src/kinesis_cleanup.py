import sys
import datetime

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
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

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

        clean = (
            self.settings.get("services", {})
            .get("kinesis", {})
            .get("stream", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_kinesis.list_streams().get("StreamNames")
            except:
                self.logging.error("Could not list all Kinesis Streams.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("kinesis", {})
                .get("stream", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource
                resource_action = "skip"

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

                    if resource_id not in self.whitelist.get("kinesis", {}).get(
                        "stream", []
                    ):
                        delta = Helper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            if resource_status == "ACTIVE":
                                try:
                                    if not self._dry_run:
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
                                        f"Kinesis Stream '{resource_id}' was created {delta.days} days ago "
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
                                f"Kinesis Stream '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Kinesis Stream '{resource_id}' has been whitelisted and has not been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "Kinesis", {}
                ).setdefault("Stream", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of Kinesis Streams.")
            return True
        else:
            self.logging.info("Skipping cleanup of Kinesis Streams.")
            return True
