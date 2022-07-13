import sys

import boto3

from src.helper import Helper


class SageMakerCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_sagemaker = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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
        """Deletes SageMaker Apps."""
        self.logging.debug("Started cleanup of SageMaker Apps.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.sagemaker.app.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.sagemaker.app.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "sagemaker.app")

        if is_cleaning_enabled:
            try:
                paginator = self.client_sagemaker.get_paginator("list_apps")
                resources = paginator.paginate().build_full_result().get("Apps")
            except:
                self.logging.error("Could not list all SageMaker Apps.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("AppName")
                resource_date = resource.get("CreationTime")
                resource_app_type = resource.get("AppType")
                resource_domain_id = resource.get("DomainId")
                resource_status = resource.get("Status")
                resource_user_profile = resource.get("UserProfileName")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_status in ("Failed", "InService"):
                            try:
                                if not self.is_dry_run:
                                    self.client_sagemaker.delete_app(
                                        AppName=resource_id,
                                        AppType=resource_app_type,
                                        DomainId=resource_domain_id,
                                        UserProfileName=resource_user_profile,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete SageMaker App '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"SageMaker App '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker App '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker App '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes SageMaker Endpoints."""
        self.logging.debug("Started cleanup of SageMaker Endpoints.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.sagemaker.endpoint.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.sagemaker.endpoint.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "sagemaker.endpoint")

        if is_cleaning_enabled:
            try:
                paginator = self.client_sagemaker.get_paginator("list_endpoints")
                resources = paginator.paginate().build_full_result().get("Endpoints")
            except:
                self.logging.error("Could not list all SageMaker Endpoints.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("EndpointName")
                resource_status = resource.get("EndpointStatus")
                resource_date = resource.get("LastModifiedTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_status in (
                            "OutOfService",
                            "InService",
                            "Failed",
                        ):
                            try:
                                if not self.is_dry_run:
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
                                    f"SageMaker Endpoint '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker Endpoint '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Endpoint '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes SageMaker Notebook Instances."""
        self.logging.debug("Started cleanup of SageMaker Notebook Instances.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.sagemaker.notebook_instance.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.sagemaker.notebook_instance.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "sagemaker.notebook_instance"
        )

        if is_cleaning_enabled:
            try:
                paginator = self.client_sagemaker.get_paginator(
                    "list_notebook_instances"
                )
                resources = paginator.paginate().build_full_result()[
                    "NotebookInstances"
                ]
            except:
                self.logging.error("Could not list all SageMaker Notebook Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("NotebookInstanceName")
                resource_status = resource.get("NotebookInstanceStatus")
                resource_date = resource.get("LastModifiedTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_status == "InService":
                            try:
                                if not self.is_dry_run:
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
                                    f"SageMaker Notebook Instance '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been stopped."
                                )
                                resource_action = "STOP"
                        elif resource_status in ("Stopped", "Failed"):
                            try:
                                if not self.is_dry_run:
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
                                    f"SageMaker Notebook Instance '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"SageMaker Notebook Instance '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"SageMaker Notebook Instance '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
