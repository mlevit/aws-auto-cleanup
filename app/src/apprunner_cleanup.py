import sys

import boto3

from src.helper import Helper


class AppRunnerCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_apprunner = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_apprunner(self):
        if not self._client_apprunner:
            self._client_apprunner = boto3.client("apprunner", region_name=self.region)
        return self._client_apprunner

    def run(self):
        self.functions()

    def functions(self):
        """
        Deletes App Runner Services.
        """

        self.logging.debug("Started cleanup of App Runner Services.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.apprunner.function.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.apprunner.function.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "apprunner.function")

        if is_cleaning_enabled:
            try:
                # TODO: Implement pagination when available.
                resources = self.client_apprunner.list_services().get(
                    "ServiceSummaryList"
                )
            except:
                self.logging.error("Could not list all App Runner Services.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ServiceName")
                resource_arn = resource.get("ServiceArn")
                resource_age = Helper.get_day_delta(resource.get("UpdatedAt")).days
                resource_action = None

                if resource_id not in resource_whitelist:
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_apprunner.delete_service(
                                    ServiceArn=resource_arn
                                )
                        except:
                            self.logging.error(
                                f"Could not delete App Runner Service '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"App Runner Service '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"App Runner Service '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"App Runner Service '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "App Runner",
                    "Service",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of App Runner Services.")
            return True
        else:
            self.logging.info("Skipping cleanup of App Runner Services.")
            return True
