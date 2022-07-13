import sys

import boto3

from src.helper import Helper


class ECSCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_ecs = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_ecs(self):
        if not self._client_ecs:
            self._client_ecs = boto3.client("ecs", region_name=self.region)
        return self._client_ecs

    def run(self):
        self.services()
        self.clusters()

    def clusters(self):
        """Deletes ECS Clusters."""
        self.logging.debug("Started cleanup of ECS Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ecs.cluster.clean", False
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ecs.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ecs.get_paginator("list_clusters")
                resources = paginator.paginate().build_full_result().get("clusterArns")
            except:
                self.logging.error("Could not list all ECS Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                try:
                    resource_details = self.client_ecs.describe_clusters(
                        clusters=[
                            resource,
                        ]
                    ).get("clusters")[0]
                except:
                    self.logging.error(
                        f"Could not get ECS Cluster's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_id = resource_details.get("clusterName")
                    resource_status = resource_details.get("status")
                    resource_running_task_count = resource_details.get(
                        "runningTasksCount"
                    )
                    resource_active_service_count = resource_details.get(
                        "activeServicesCount"
                    )
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_status not in ("ACTIVE", "FAILED"):
                            self.logging.warn(
                                f"ECS Cluster '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                        elif resource_active_service_count > 0:
                            self.logging.debug(
                                f"ECS Cluster '{resource_id}' has {resource_active_service_count} active services running and cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                        elif resource_running_task_count > 0:
                            self.logging.debug(
                                f"ECS Cluster '{resource_id}' has {resource_running_task_count} running tasks and cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                        else:
                            try:
                                if not self.is_dry_run:
                                    self.client_ecs.delete_cluster(
                                        cluster=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete ECS Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"ECS Cluster '{resource_id}' has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ECS Cluster '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ECS",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of ECS Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of ECS Clusters.")
            return True

    def services(self):
        """Deletes ECS Services."""
        self.logging.debug("Started cleanup of ECS Services.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ecs.service.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ecs.service.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ecs.service")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ecs.get_paginator("list_clusters")
                clusters = paginator.paginate().build_full_result().get("clusterArns")
            except:
                self.logging.error("Could not list all ECS Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            for cluster in clusters:
                try:
                    paginator = self.client_ecs.get_paginator("list_services")
                    resources = paginator.paginate(cluster=cluster).build_full_result()[
                        "serviceArns"
                    ]
                except:
                    self.logging.error(
                        f"Could not list all ECS Services for Cluster '{cluster}'."
                    )
                    self.logging.error(sys.exc_info()[1])
                    return False

                for resource in resources:
                    try:
                        resource_details = self.client_ecs.describe_services(
                            cluster=cluster,
                            services=[
                                resource,
                            ],
                        ).get("services")[0]
                    except:
                        self.logging.error(
                            f"Could not get ECS Service's '{resource}' details."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        resource_id = resource_details.get("serviceName")
                        resource_status = resource_details.get("status")
                        resource_date = resource_details.get("createdAt")
                        resource_age = Helper.get_day_delta(resource_date).days
                        resource_action = None

                        if Helper.not_allowlisted(resource_id, resource_allowlist):
                            if resource_age > resource_maximum_age:
                                if resource_status in ("ACTIVE", "INACTIVE"):
                                    try:
                                        if not self.is_dry_run:
                                            self.client_ecs.delete_service(
                                                cluster=cluster,
                                                service=resource_id,
                                                force=True,
                                            )
                                    except:
                                        self.logging.error(
                                            f"Could not delete ECS Service '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.info(
                                            f"ECS Service '{resource_id}' was created {resource_age} days ago "
                                            "and has been deleted."
                                        )
                                        resource_action = "DELETE"
                                else:
                                    self.logging.warn(
                                        f"ECS Service '{resource_id}' in state '{resource_status}' cannot be deleted."
                                    )
                                    resource_action = "SKIP - IN USE"
                            else:
                                self.logging.debug(
                                    f"ECS Service '{resource_id}' was created {resource_age} days ago "
                                    "(less than TTL setting) and has not been deleted."
                                )
                                resource_action = "SKIP - TTL"
                        else:
                            self.logging.debug(
                                f"ECS Service '{resource_id}' has been allowlisted and has not been deleted."
                            )
                            resource_action = "SKIP - ALLOWLIST"

                    Helper.record_execution_log_action(
                        self.execution_log,
                        self.region,
                        "ECS",
                        "Service",
                        resource_id,
                        resource_action,
                    )

            self.logging.debug("Finished cleanup of ECS Services.")
            return True
        else:
            self.logging.info("Skipping cleanup of ECS Services.")
            return True
