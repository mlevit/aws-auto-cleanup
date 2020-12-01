import sys

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
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_sagemaker(self):
        if not self._client_sagemaker:
            self._client_sagemaker = boto3.client("sagemaker", region_name=self.region)
        return self._client_sagemaker

    def run(self):
        self.apps()
        self.endpoints()
        self.notebook_instances()

    def apps(self):
        """
        Deletes SageMaker Apps.
        """

        self.logging.debug("Started cleanup of SageMaker Apps.")

        clean = (
            self.settings.get("services", {})
            .get("sagemaker", {})
            .get("app", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_sagemaker.list_apps().get("Apps")
            except:
                self.logging.error("Could not list all SageMaker Apps.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("sagemaker", {})
                .get("app", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("AppName")
                resource_date = resource.get("CreationTime")
                resource_app_type = resource.get("AppType")
                resource_domain_id = resource.get("DomainId")
                resource_status = resource.get("Status")
                resource_user_profile = resource.get("UserProfileName")
                resource_action = None

                if resource_id not in self.whitelist.get("sagemaker", {}).get(
                    "app", []
                ):
                    delta = Helper.get_day_delta(resource_date)
                    if delta.days > ttl_days:
                        if resource_status in ("Failed", "InService"):
                            try:
                                if not self._dry_run:
                                    self.client_sagemaker.delete_app(
                                        DomainId=resource_domain_id,
                                        UserProfileName=resource_user_profile,
                                        AppType=resource_app_type,
                                        AppName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete SageMaker App '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"SageMaker App '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker App '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker App '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "SageMaker",
                    "App",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of SageMaker Apps.")
            return True
        else:
            self.logging.info("Skipping cleanup of SageMaker Apps.")
            return True

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
                resource_action = None

                if resource_id not in self.whitelist.get("sagemaker", {}).get(
                    "endpoint", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status in (
                            "OutOfService",
                            "InService",
                            "Failed",
                        ):
                            try:
                                if not self._dry_run:
                                    self.client_sagemaker.delete_endpoint(
                                        EndpointName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete SageMaker Endpoint '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"SageMaker Endpoint '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker Endpoint '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Endpoint '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "SageMaker",
                    "Endpoint",
                    resource_id,
                    resource_action,
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
                resource_action = None

                if resource_id not in self.whitelist.get("sagemaker", {}).get(
                    "notebook_instance", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status == "InService":
                            try:
                                if not self._dry_run:
                                    self.client_sagemaker.stop_notebook_instance(
                                        NotebookInstanceName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not stop SageMaker Notebook Instance '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"SageMaker Notebook Instance '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been stopped."
                                )
                                resource_action = "STOP"
                        elif resource_status in ("Stopped", "Failed"):
                            try:
                                if not self._dry_run:
                                    self.client_sagemaker.delete_notebook_instance(
                                        NotebookInstanceName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete SageMaker Notebook Instance '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"SageMaker Notebook Instance '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker Notebook Instance '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Notebook Instance '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "SageMaker",
                    "Notebook Instance",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of SageMaker Notebook Instances.")
            return True
        else:
            self.logging.info("Skipping cleanup of SageMaker Notebook Instances.")
            return True
