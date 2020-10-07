import sys
import datetime

import boto3

import helper


class EMRCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_emr = None

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
                resource_action = "skip"

                if resource_id not in self.whitelist.get("emr", {}).get("cluster", []):
                    delta = helper.Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status in ("RUNNING", "WAITING"):
                            if not self.settings.get("general", {}).get(
                                "dry_run", True
                            ):
                                try:
                                    self.client_emr.terminate_job_flows(
                                        JobFlowIds=[resource_id]
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete EMR Cluster '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "error"
                                    continue

                            self.logging.info(
                                f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "delete"
                        else:
                            self.logging.error(
                                f"EMR Cluster '%s' in state '%s' cannot be deleted."
                                % (resource_id, resource_status)
                            )
                            resource_action = "error"
                    else:
                        self.logging.debug(
                            f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"EMR Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "EMR", {}
                ).setdefault("Cluster", []).append(
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
            self.logging.info("Skipping cleanup of EMR Clusters.")
            return True
