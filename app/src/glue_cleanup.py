import sys

import boto3

from src.helper import Helper


class GlueCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_glue = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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
        """Deletes Glue Crawlers."""
        self.logging.debug("Started cleanup of Glue Crawlers.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.glue.crawler.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.glue.crawler.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "glue.crawler")

        if is_cleaning_enabled:
            try:
                paginator = self.client_glue.get_paginator("get_crawlers")
                resources = paginator.paginate().build_full_result().get("Crawlers")
            except:
                self.logging.error("Could not list all Glue Crawlers.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("Name")
                resource_date = resource.get("LastUpdated")
                resource_status = resource.get("State")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_status != "RUNNING":
                            try:
                                if not self.is_dry_run:
                                    self.client_glue.delete_crawler(Name=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete Glue Crawler '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Glue Crawler '{resource_id}' was last modified {resource_age} days ago "
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
                            f"Glue Crawler '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Crawler '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes Glue Databases."""
        self.logging.debug("Started cleanup of Glue Databases.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.glue.database.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.glue.database.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "glue.database")

        if is_cleaning_enabled:
            try:
                paginator = self.client_glue.get_paginator("get_databases")
                resources = paginator.paginate().build_full_result().get("DatabaseList")
            except:
                self.logging.error("Could not list all Glue Databases.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("Name")
                resource_date = resource.get("CreateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_glue.delete_database(Name=resource_id)
                        except:
                            self.logging.error(
                                f"Could not delete Glue Database '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Glue Database '{resource_id}' was created {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Glue Database '{resource_id}' was created {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Database '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes Glue Dev Endpoints."""
        self.logging.debug("Started cleanup of Glue Dev Endpoints.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.glue.dev_endpoint.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.glue.dev_endpoint.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "glue.dev_endpoint")

        if is_cleaning_enabled:
            try:
                paginator = self.client_glue.get_paginator("get_dev_endpoints")
                resources = paginator.paginate().build_full_result().get("DevEndpoints")
            except:
                self.logging.error("Could not list all Glue Dev Endpoints.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("EndpointName")
                resource_date = resource.get("LastModifiedTimestamp")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
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
                                f"Glue Dev Endpoint '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Glue Dev Endpoint '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Glue Dev Endpoint '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
