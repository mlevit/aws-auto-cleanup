import sys
import datetime

import boto3

from src.helper import Helper


class BatchCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_batch = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_batch(self):
        if not self._client_batch:
            self._client_batch = boto3.client("batch", region_name=self.region)
        return self._client_batch

    def run(self):
        self.job_queues()
        self.layers()

    def job_queues(self):
        """
        Deletes Batch Job Queues.
        """

        self.logging.debug("Started cleanup of Batch Job Queues.")

        clean = (
            self.settings.get("services", {})
            .get("batch", {})
            .get("job_queue", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_batch.describe_job_queues().get("jobQueues")
            except:
                self.logging.error("Could not list all Batch Job Queues.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("batch", {})
                .get("job_queue", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("jobQueueName")
                resource_state = resource.get("state")
                resource_environments = resource.get("computeEnvironmentOrder")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("batch", {}).get(
                    "job_queue", []
                ):
                    if len(resource_environments) == 0:
                        if resource_state == "ENABLED":
                            try:
                                if not self._dry_run:
                                    self.client_batch.update_job_queue(
                                        jobQueue=resource_id,
                                        state="DISABLED",
                                    )
                            except:
                                self.logging.error(
                                    f"Could not disable Batch Job Queue '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Batch Job Queue '{resource_id}' has been disabled."
                                )

                        if resource_action != "ERROR":
                            try:
                                if not self._dry_run:
                                    self.client_batch.delete_job_queue(
                                        jobQueue=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete Batch Job Queue '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Batch Job Queue '{resource_id}' is not associated with any Compute Environments "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Batch Job Queue '{resource_id}' is associate with {len(resource_environments)} Compute Environment(s) and has not been deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"Batch Job Queue '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "Batch", {}
                ).setdefault("Job Queue", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of Batch Job Queues.")
            return True
        else:
            self.logging.info("Skipping cleanup of Batch Job Queues.")
            return True

    def layers(self):
        pass
