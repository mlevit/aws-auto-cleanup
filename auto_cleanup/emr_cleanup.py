import sys

import boto3

from . import lambda_helper


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
            .get("clusters", {})
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
                .get("clusters", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("Id")
                resource_date = (
                    resource.get("Status").get("Timeline").get("CreationDateTime")
                )
                resource_status = resource.get("Status").get("State")

                if resource_id not in self.whitelist.get("emr", {}).get("cluster", []):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

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
                                    continue

                            self.logging.info(
                                f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                        else:
                            self.logging.debug(
                                f"EMR Cluster '%s' in state '%s' cannot be deleted."
                                % (resource_id, resource_status)
                            )
                    else:
                        self.logging.debug(
                            f"EMR Cluster '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"EMR Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "EMR", {}
                ).setdefault("Clusters", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of EMR Clusters.")
            return True
