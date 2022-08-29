import sys

import boto3

from src.helper import Helper


class ECRCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_ecr = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_ecr(self):
        if not self._client_ecr:
            self._client_ecr = boto3.client("ecr", region_name=self.region)
        return self._client_ecr

    def run(self):
        self.repositories()

    def repositories(self):
        """Deletes ECR Repositories."""
        self.logging.debug("Started cleanup of ECR Repositories.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ecr.repository.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ecr.repository.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ecr.repository")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ecr.get_paginator("describe_repositories")
                resources = paginator.paginate().build_full_result().get("repositories")
            except:
                self.logging.error("Could not list all ECR Repositories.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("repositoryName")
                resource_date = resource.get("createdAt")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                # for each repository, we must first delete all the
                # images before deleting the repository itself
                self.images(resource_id)

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    try:
                        paginator = self.client_ecr.get_paginator("list_images")
                        list_images = (
                            paginator.paginate(repositoryName=resource_id)
                            .build_full_result()
                            .get("imageIds")
                        )
                    except:
                        self.logging.error(
                            f"Could not list all ECR Images for ECR Repository '{resource_id}'."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        if len(list_images) == 0:
                            if resource_age > resource_maximum_age:
                                try:
                                    if not self.is_dry_run:
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
                                        f"ECR Repository '{resource_id}' was created {resource_age} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "DELETE"
                            else:
                                self.logging.debug(
                                    f"ECR Repository '{resource_id}' was created {resource_age} days ago "
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
                        f"ECR Repository '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ECR",
                    "Repository",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of ECR Repositories.")
            return True
        else:
            self.logging.info("Skipping cleanup of ECR Repositories.")
            return True

    def images(self, repository):
        """Deletes ECR Images for a Repository."""
        self.logging.debug(
            f"Started cleanup of ECR Images for ECR Repository '{repository}'."
        )

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ecr.image.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ecr.image.ttl", 7
        )
        allowlisted_resources = Helper.get_allowlist(self.allowlist, "ecr.image")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ecr.get_paginator("describe_images")
                resources = (
                    paginator.paginate(repositoryName=repository)
                    .build_full_result()
                    .get("imageDetails")
                )
            except:
                self.logging.error(
                    f"Could not list all ECR Images for ECR Repository '{repository}'."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("imageDigest")
                resource_date = resource.get("imagePushedAt")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_id not in allowlisted_resources:
                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
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
                                f"ECR Image '{resource_id}' was pushed {resource_age} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"ECR Image '{resource_id}' was pushed {resource_age} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"ECR Image '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "ECR",
                    "Image",
                    resource_id,
                    resource_action,
                )

            self.logging.debug(
                f"Finished cleanup of ECR Images for ECR Repository '{repository}'."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of ECR Images for ECR Repository '{repository}'."
            )
            return True
