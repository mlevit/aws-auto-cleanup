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
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.emr.cluster.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.emr.cluster.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "emr.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_emr.get_paginator("list_clusters")
                resources = paginator.paginate().build_full_result()["Clusters"]
            except:
                self.logging.error("Could not list all EMR Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource["Id"]
                resource_date = resource["Status"]["Timeline"]["CreationDateTime"]
                resource_status = resource["Status"]["State"]
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_id not in resource_whitelist:
                    if resource_age > maximum_resource_age:
                        if resource_status in ("RUNNING", "WAITING"):
                            try:
                                if not self.is_dry_run:
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
                                    f"EMR Cluster '{resource_id}' was created {resource_age} days ago "
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
                            f"EMR Cluster '{resource_id}' was created {resource_age} days ago "
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
