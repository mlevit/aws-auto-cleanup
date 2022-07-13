import sys

import boto3
import botocore

from src.helper import Helper


class AirflowCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_airflow = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_airflow(self):
        if not self._client_airflow:
            self._client_airflow = boto3.client("mwaa", region_name=self.region)
        return self._client_airflow

    def run(self):
        self.environments()

    def environments(self):
        """Deletes Airflow Environments."""
        self.logging.debug("Started cleanup of Airflow Environments.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.airflow.environment.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.airflow.environment.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "airflow.environment")

        if is_cleaning_enabled:
            try:
                paginator = self.client_airflow.get_paginator("list_environments")
                resources = paginator.paginate().build_full_result().get("Environments")
            except botocore.exceptions.EndpointConnectionError:
                self.logging.debug(f"Airflow is not enabled in region '{self.region}'.")
                return False
            except:
                self.logging.error("Could not list all Airflow Environments.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                try:
                    resource_details = self.client_airflow.get_environment(
                        Name=resource
                    ).get("Environment")
                except:
                    self.logging.error(
                        f"Could not get Airflow Environment's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_date = resource_details.get("CreatedAt")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_airflow.delete_environment(
                                        Name=resource
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete Airflow Environment '{resource}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Airflow Environment '{resource}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"Airflow Environment '{resource}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Airflow Environment '{resource}' has been allowlisted and has not "
                            "been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Airflow",
                    "Environment",
                    resource,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Airflow Environments.")
            return True
        else:
            self.logging.info("Skipping cleanup of Airflow Environments.")
            return True
