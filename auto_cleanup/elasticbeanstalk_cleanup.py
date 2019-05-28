import sys

import boto3

from . import lambda_helper


class ElasticBeanstalkCleanup:
    def __init__(self, logging, whitelist, settings, resource_tree, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = region

        self._client_elasticbeanstalk = None

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

        clean = (
            self.settings.get("services", {})
            .get("elasticbeanstalk", {})
            .get("applications", {})
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
                .get("applications", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ApplicationName")
                resource_date = resource.get("DateUpdated")

                if resource_id not in self.whitelist.get("elasticbeanstalk", {}).get(
                    "application", []
                ):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            try:
                                self.client_elasticbeanstalk.delete_application(
                                    ApplicationName=resource_id,
                                    TerminateEnvByForce=True,
                                )
                            except:
                                self.logging.error(
                                    f"Could not delete Elastic Beanstalk Application '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                        self.logging.info(
                            f"Elastic Beanstalk Application '{resource_id}' was last modified {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"Elastic Beanstalk Application '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"Elastic Beanstalk Application '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "Elastic Beanstalk", {}
                ).setdefault("Applications", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of Elastic Beanstalk Applications.")
            return True
