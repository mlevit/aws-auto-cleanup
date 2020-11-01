import sys
import datetime

import boto3

from src.helper import Helper


class ElasticBeanstalkCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticbeanstalk = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_elasticbeanstalk(self):
        if not self._client_elasticbeanstalk:
            self._client_elasticbeanstalk = boto3.client(
                "elasticbeanstalk", region_name=self.region
            )
        return self._client_elasticbeanstalk

    def run(self):
        self.applications()

    def applications(self):
        """
        Deletes Elastic Beanstalk Applications.
        """

        self.logging.debug("Started cleanup of Elastic Beanstalk Applications.")

        clean = (
            self.settings.get("services", {})
            .get("elasticbeanstalk", {})
            .get("application", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_elasticbeanstalk.describe_applications().get(
                    "Applications"
                )
            except:
                self.logging.error("Could not list all ElasticBeanstalk Applications.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("elasticbeanstalk", {})
                .get("application", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ApplicationName")
                resource_date = resource.get("DateUpdated")
                resource_action = None

                if resource_id not in self.whitelist.get("elasticbeanstalk", {}).get(
                    "application", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_elasticbeanstalk.delete_application(
                                    ApplicationName=resource_id,
                                    TerminateEnvByForce=True,
                                )
                        except:
                            self.logging.error(
                                f"Could not delete Elastic Beanstalk Application '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Elastic Beanstalk Application '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Elastic Beanstalk Application '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Elastic Beanstalk Application '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "Elastic Beanstalk", {}
                ).setdefault("Application", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of Elastic Beanstalk Applications.")
            return True
        else:
            self.logging.info("Skipping cleanup of Elastic Beanstalk Applications.")
            return True
