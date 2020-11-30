import sys

import boto3

from src.helper import Helper


class AirflowCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_airflow = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_airflow(self):
        if not self._client_airflow:
            self._client_airflow = boto3.client("mwaa", region_name=self.region)
        return self._client_airflow

    def run(self):
        self.environments()

    def environments(self):
        """
        Deletes Airflow Environments.
        """

        self.logging.debug("Started cleanup of Airflow Environments.")

        clean = (
            self.settings.get("services", {})
            .get("airflow", {})
            .get("environment", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_airflow.list_environments().get("Environments")
            except:
                self.logging.error("Could not list all Airflow Environments.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("airflow", {})
                .get("environment", {})
                .get("ttl", 7)
            )

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
                    resource_action = None

                    if resource not in self.whitelist.get("airflow", {}).get(
                        "environment", []
                    ):
                        delta = Helper.get_day_delta(resource_date)
                        if delta.days > ttl_days:
                            try:
                                if not self._dry_run:
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
                                    f"Airflow Environment '{resource}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"Airflow Environment '{resource}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Airflow Environment '{resource}' has been whitelisted and has not "
                            "been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

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
