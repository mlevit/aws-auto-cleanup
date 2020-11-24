import sys
import datetime

import boto3

from src.helper import Helper


class GlueCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_glue = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_glue(self):
        if not self._client_glue:
            self._client_glue = boto3.client("glue", region_name=self.region)
        return self._client_glue

    def run(self):
        self.crawlers()
        self.databases()
        self.dev_endpoints()

    def crawlers(self):
        """
        Deletes Glue Crawlers.
        """

        self.logging.debug("Started cleanup of Glue Crawlers.")

        clean = (
            self.settings.get("services", {})
            .get("glue", {})
            .get("crawler", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_glue.get_paginator("get_crawlers")
                response_iterator = paginator.paginate().build_full_result()
            except:
                self.logging.error("Could not list all Glue Crawlers.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("glue", {})
                .get("crawler", {})
                .get("ttl", 7)
            )

            for resource in response_iterator.get("Crawlers"):
                resource_id = resource.get("Name")
                resource_date = resource.get("LastUpdated")
                resource_status = resource.get("State")
                resource_action = None

                if resource_id not in self.whitelist.get("glue", {}).get("crawler", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if resource_status != "RUNNING":
                            try:
                                if not self._dry_run:
                                    self.client_glue.delete_crawler(Name=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete Glue Crawler '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Glue Crawler '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.warn(
                                f"Glue Crawler '{resource_id}' in state '{resource_status}' cannot be deleted."
                            )
                            resource_action = "SKIP - IN USE"
                    else:
                        self.logging.debug(
                            f"Glue Crawler '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Crawler '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Glue",
                    "Crawler",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Glue Crawlers.")
            return True
        else:
            self.logging.info("Skipping cleanup of Glue Crawlers.")
            return True

    def databases(self):
        """
        Deletes Glue Databases.
        """

        self.logging.debug("Started cleanup of Glue Databases.")

        clean = (
            self.settings.get("services", {})
            .get("glue", {})
            .get("database", {})
            .get("clean", False)
        )
        if clean:
            try:
                paginator = self.client_glue.get_paginator("get_databases")
                response_iterator = paginator.paginate().build_full_result()
            except:
                self.logging.error("Could not list all Glue Databases.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("glue", {})
                .get("database", {})
                .get("ttl", 7)
            )

            for resource in response_iterator.get("DatabaseList"):
                resource_id = resource.get("Name")
                resource_date = resource.get("CreateTime")
                resource_action = None

                if resource_id not in self.whitelist.get("glue", {}).get(
                    "database", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_glue.delete_database(Name=resource_id)
                        except:
                            self.logging.error(
                                f"Could not delete Glue Database '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Glue Database '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Glue Database '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Database '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Glue",
                    "Database",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Glue Databases.")
            return True
        else:
            self.logging.info("Skipping cleanup of Glue Databases.")
            return True

    def dev_endpoints(self):
        """
        Deletes Glue Dev Endpoints.
        """

        self.logging.debug("Started cleanup of Glue Dev Endpoints.")

        clean = (
            self.settings.get("services", {})
            .get("glue", {})
            .get("dev_endpoint", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_glue.get_dev_endpoints().get("DevEndpoints")
            except:
                self.logging.error("Could not list all Glue Dev Endpoints.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("glue", {})
                .get("dev_endpoint", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("EndpointName")
                resource_date = resource.get("LastModifiedTimestamp")
                resource_action = None

                if resource_id not in self.whitelist.get("glue", {}).get(
                    "dev_endpoint", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_glue.delete_dev_endpoint(
                                    EndpointName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete Glue Dev Endpoint '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Glue Dev Endpoint '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Glue Dev Endpoint '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Dev Endpoint '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Glue",
                    "Dev Endpoint",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Glue Dev Endpoints.")
            return True
        else:
            self.logging.info("Skipping cleanup of Glue Dev Endpoints.")
            return True
