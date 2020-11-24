import sys

import boto3

from src.helper import Helper


class EMRCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_emr = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_emr(self):
        if not self._client_emr:
            self._client_emr = boto3.client("emr", region_name=self.region)
        return self._client_emr

    def run(self):
        self.clusters()

    def clusters(self):
        """
        Deletes EMR Clusters.
        """

        self.logging.debug("Started cleanup of EMR Clusters.")

        clean = (
            self.settings.get("services", {})
            .get("emr", {})
            .get("cluster", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_emr.list_clusters().get("Clusters")
            except:
                self.logging.error("Could not list all EMR Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("emr", {})
                .get("cluster", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("Id")
                resource_date = (
                    resource.get("Status").get("Timeline").get("CreationDateTime")
                )
                resource_status = resource.get("Status").get("State")
                resource_action = None

                if resource_id not in self.whitelist.get("emr", {}).get("cluster", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status in ("RUNNING", "WAITING"):
                            try:
                                if not self._dry_run:
                                    self.client_emr.terminate_job_flows(
                                        JobFlowIds=[resource_id]
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete EMR Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.warn(
                                f"EMR Cluster '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                    else:
                        self.logging.debug(
                            f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EMR Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EMR",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EMR Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of EMR Clusters.")
            return True
