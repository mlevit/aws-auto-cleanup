import sys

import boto3

from src.helper import Helper


class AmplifyCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_amplify = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_amplify(self):
        if not self._client_amplify:
            self._client_amplify = boto3.client("amplify", region_name=self.region)
        return self._client_amplify

    def run(self):
        self.apps()

    def apps(self):
        """Deletes Amplify Apps."""
        self.logging.debug("Started cleanup of Amplify Apps.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.amplify.app.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.amplify.app.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "amplify.app")

        if is_cleaning_enabled:
            try:
                paginator = self.client_amplify.get_paginator("list_apps")
                resources = paginator.paginate().build_full_result().get("apps")
            except:
                self.logging.error("Could not list all Amplify Apps.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("name")
                resource_app_id = resource.get("appId")
                resource_date = resource.get("updateTime")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_amplify.delete_app(appId=resource_app_id)
                        except:
                            self.logging.error(
                                f"Could not delete Amplify App '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Amplify App '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Amplify App '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Amplify App '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Amplify",
                    "App",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Amplify Apps.")
            return True
        else:
            self.logging.info("Skipping cleanup of Amplify Apps.")
            return True
