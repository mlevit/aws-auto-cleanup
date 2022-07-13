import sys

import boto3

from src.helper import Helper


class ElasticBeanstalkCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticbeanstalk = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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
        """Deletes Elastic Beanstalk Applications."""
        self.logging.debug("Started cleanup of Elastic Beanstalk Applications.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.elastic_beanstalk.application.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.elastic_beanstalk.application.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "elastic_beanstalk.application"
        )

        if is_cleaning_enabled:
            try:
                resources = self.client_elasticbeanstalk.describe_applications().get(
                    "Applications"
                )
            except:
                self.logging.error("Could not list all ElasticBeanstalk Applications.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ApplicationName")
                resource_date = resource.get("DateUpdated")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
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
                                f"Elastic Beanstalk Application '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Elastic Beanstalk Application '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"Elastic Beanstalk Application '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Elastic Beanstalk",
                    "Application",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Elastic Beanstalk Applications.")
            return True
        else:
            self.logging.info("Skipping cleanup of Elastic Beanstalk Applications.")
            return True
