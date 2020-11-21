import sys
import datetime

import boto3

from src.helper import Helper


class ECRCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_ecr = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_ecr(self):
        if not self._client_ecr:
            self._client_ecr = boto3.client("ecr", region_name=self.region)
        return self._client_ecr

    def run(self):
        self.repositories()

    def repositories(self):
        """
        Deletes ECR Repositories.
        """

        self.logging.debug("Started cleanup of ECR Repositories.")

        clean = (
            self.settings.get("services", {})
            .get("ecr", {})
            .get("repository", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ecr.describe_repositories().get("repositories")
            except:
                self.logging.error("Could not list all ECR Repositories.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ecr", {})
                .get("repository", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("repositoryName")
                resource_date = resource.get("createdAt")
                resource_action = None

                # for each repository, we must first delete all the
                # images before deleting the repository itself
                self.images(resource_id)

                if resource_id not in self.whitelist.get("ecr", {}).get(
                    "repository", []
                ):
                    list_images = self.client_ecr.list_images(
                        repositoryName=resource_id,
                    ).get("imageIds")

                    delta = Helper.get_day_delta(resource_date)

                    if len(list_images) == 0:
                        if delta.days > ttl_days:
                            try:
                                if not self._dry_run:
                                    self.client_ecr.delete_repository(
                                        repositoryName=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete ECR Repository '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"ECR Repository '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"ECR Repository '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"ECR Repository '{resource_id}' contains ECR Images and has not been deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"ECR Repository '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "ECR", {}
                ).setdefault("Repository", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of ECR Repositories.")
            return True
        else:
            self.logging.info("Skipping cleanup of ECR Repositories.")
            return True

    def images(self, repository):
        """
        Deletes ECR Images for a Repository.
        """

        self.logging.debug(
            f"Started cleanup of ECR Images for ECR Repository {repository}."
        )

        clean = (
            self.settings.get("services", {})
            .get("ecr", {})
            .get("image", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ecr.describe_images(
                    repositoryName=repository
                ).get("imageDetails")
            except:
                self.logging.error(
                    f"Could not list all ECR Images for ECR Repository {repository}."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ecr", {})
                .get("image", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("imageDigest")
                resource_date = resource.get("imagePushedAt")
                resource_action = None

                if resource_id not in self.whitelist.get("ecr", {}).get("image", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_ecr.batch_delete_image(
                                    repositoryName=repository,
                                    imageIds=[{"imageDigest": resource_id}],
                                )
                        except:
                            self.logging.error(
                                f"Could not delete ECR Image '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"ECR Image '{resource_id}' was pushed {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ECR Image '{resource_id}' was pushed {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"ECR Image '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "ECR", {}
                ).setdefault("Image", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug(
                f"Finished cleanup of ECR Images for ECR Repository {repository}."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of ECR Images for ECR Repository {repository}."
            )
            return True
