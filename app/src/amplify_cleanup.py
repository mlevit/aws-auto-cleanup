import sys

import boto3

from src.helper import Helper


class AmplifyCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_amplify = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_amplify(self):
        if not self._client_amplify:
            self._client_amplify = boto3.client("amplify", region_name=self.region)
        return self._client_amplify

    def run(self):
        self.apps()

    def apps(self):
        """
        Deletes Amplify Apps.
        """

        self.logging.debug("Started cleanup of Amplify Apps.")

        clean = (
            self.settings.get("services", {})
            .get("amplify", {})
            .get("app", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_amplify.list_apps().get("apps")
            except:
                self.logging.error("Could not list all Amplify Apps.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("amplify", {})
                .get("app", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("name")
                resource_app_id = resource.get("appId")
                resource_date = resource.get("updateTime")
                resource_action = None

                if resource_id not in self.whitelist.get("amplify", {}).get("app", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_amplify.delete_app(appId=resource_app_id)
                        except:
                            self.logging.error(
                                f"Could not delete Amplify App '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Amplify App '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Amplify App '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Amplify App '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

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
