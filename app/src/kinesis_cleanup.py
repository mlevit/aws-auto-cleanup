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

                try:
                    resource_details = self.client_kinesis.describe_stream(
                        StreamName=resource_id
                    ).get("StreamDescription")
                except:
                    self.logging.error(
                        f"Could not get Kinesis Stream's '{resource_id}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "error"
                    return False

                resource_status = resource_details.get("StreamStatus")
                resource_date = resource_details.get("StreamCreationTimestamp")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("kinesis", {}).get(
                    "stream", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            if resource_status == "ACTIVE":
                                try:
                                    self.client_kinesis.delete_stream(
                                        StreamName=resource_id,
                                        EnforceConsumerDeletion=True,
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete Kinesis Stream '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "error"
                                    continue
                            else:
                                self.logging.error(
                                    f"Kinesis Stream '{resource_id}' in state '{resource_status}' cannot be deleted."
                                )
                                resource_action = "error"

                        self.logging.info(
                            f"Kinesis Stream '{resource_id}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                        resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"Kinesis Stream '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"Kinesis Stream '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

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
            return True
        else:
            self.logging.info("Skipping cleanup of Kinesis Streams.")
            return True
