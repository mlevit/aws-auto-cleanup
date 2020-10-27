import sys
import datetime

import boto3

from src.helper import Helper


class SageMakerCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_sagemaker = None

    @property
    def client_sagemaker(self):
        if not self._client_sagemaker:
            self._client_sagemaker = boto3.client("sagemaker", region_name=self.region)
        return self._client_sagemaker

    def run(self):
        self.endpoints()
        self.notebook_instances()

    def endpoints(self):
        """
        Deletes SageMaker Endpoints.
        """

        self.logging.debug("Started cleanup of SageMaker Endpoints.")

        clean = (
            self.settings.get("services", {})
            .get("sagemaker", {})
            .get("endpoint", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_sagemaker.list_endpoints().get("Endpoints")
            except:
                self.logging.error("Could not list all SageMaker Endpoints.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("sagemaker", {})
                .get("endpoint", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("EndpointName")
                resource_status = resource.get("EndpointStatus")
                resource_date = resource.get("LastModifiedTime")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("sagemaker", {}).get(
                    "endpoint", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            if resource_status in (
                                "OutOfService",
                                "InService",
                                "Failed",
                            ):
                                try:
                                    self.client_sagemaker.delete_endpoint(
                                        EndpointName=resource_id,
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete SageMaker Endpoint '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "error"
                                    continue
                                else:
                                    self.logging.info(
                                        f"SageMaker Endpoint '{resource_id}' was last modified {delta.days} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"SageMaker Endpoint '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Endpoint '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "SageMaker", {}
                ).setdefault("Endpoint", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of SageMaker Endpoints.")
            return True
        else:
            self.logging.info("Skipping cleanup of SageMaker Endpoints.")
            return True

    def notebook_instances(self):
        """
        Deletes SageMaker Notebook Instances.
        """

        self.logging.debug("Started cleanup of SageMaker Notebook Instances.")

        clean = (
            self.settings.get("services", {})
            .get("sagemaker", {})
            .get("notebook_instance", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_sagemaker.list_notebook_instances().get(
                    "NotebookInstances"
                )
            except:
                self.logging.error("Could not list all SageMaker Notebook Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("sagemaker", {})
                .get("notebook_instance", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("NotebookInstanceName")
                resource_status = resource.get("NotebookInstanceStatus")
                resource_date = resource.get("LastModifiedTime")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("sagemaker", {}).get(
                    "notebook_instance", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status == "InService":
                            if not self.settings.get("general", {}).get(
                                "dry_run", True
                            ):
                                try:
                                    self.client_sagemaker.stop_notebook_instance(
                                        NotebookInstanceName=resource_id,
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not stop SageMaker Notebook Instance '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "error"
                                    continue

                            self.logging.info(
                                f"SageMaker Notebook Instance '{resource_id}' was last modified {delta.days} days ago "
                                "and has been stopped."
                            )
                            resource_action = "stop"
                        elif resource_status in ("Stopped", "Failed"):
                            if not self.settings.get("general", {}).get(
                                "dry_run", True
                            ):
                                try:
                                    self.client_sagemaker.delete_notebook_instance(
                                        NotebookInstanceName=resource_id,
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete SageMaker Notebook Instance '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "error"
                                    continue

                            self.logging.info(
                                f"SageMaker Notebook Instance '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "delete"
                    else:
                        self.logging.debug(
                            f"SageMaker Notebook Instance '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "skip - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Notebook Instance '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "skip - whitelist"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "SageMaker", {}
                ).setdefault("Notebook Instance", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of SageMaker Notebook Instances.")
            return True
        else:
            self.logging.info("Skipping cleanup of SageMaker Notebook Instances.")
            return True
