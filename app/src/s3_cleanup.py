import sys
import datetime

import boto3

from src.helper import Helper


class S3Cleanup:
    def __init__(self, logging, whitelist, settings, execution_log):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = "global"

        self._client_s3 = None
        self._resource_s3 = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_s3(self):
        if not self._client_s3:
            self._client_s3 = boto3.client("s3")
        return self._client_s3

    @property
    def resource_s3(self):
        if not self._resource_s3:
            self._resource_s3 = boto3.resource("s3")
        return self._resource_s3

    def run(self):
        self.buckets()

    def buckets(self):
        """
        Deletes Buckets. All Bucket Objects, Versions and Deleted Markers
        are first deleted before the Bucket can be deleted.
        """

        self.logging.debug("Started cleanup of S3 Buckets.")

        clean = (
            self.settings.get("services", {})
            .get("s3", {})
            .get("bucket", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_s3.list_buckets()
            except:
                self.logging.error("Could not list all S3 Buckets.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("s3", {})
                .get("bucket", {})
                .get("ttl", 7)
            )

            for resource in resources.get("Buckets"):
                resource_id = resource.get("Name")
                resource_date = resource.get("CreationDate")
                resource_action = "skip"

                if resource_id not in self.whitelist.get("s3", {}).get("bucket", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        # delete bucket policy
                        try:
                            if not self._dry_run:
                                self.client_s3.delete_bucket_policy(Bucket=resource_id)
                        except:
                            self.logging.error(
                                f"Could not delete Bucket Policy for S3 Bucket '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Deleted Bucket Policy for S3 Bucket '{resource_id}'."
                            )

                            bucket_resource = self.resource_s3.Bucket(resource_id)

                            # delete all objects
                            try:
                                if not self._dry_run:
                                    bucket_resource.objects.delete()
                            except:
                                self.logging.error(
                                    f"Could not delete all Objects from S3 Bucket '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Deleted all Objects from S3 Bucket '{resource_id}'."
                                )

                                # delete all Versions and DeleteMarkers
                                try:
                                    if not self._dry_run:
                                        bucket_resource.object_versions.delete()
                                except:
                                    self.logging.error(
                                        f"Could not get all Versions and Delete Markers from S3 Bucket '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.info(
                                        f"Deleted all Versions and Delete Markers from S3 Bucket '{resource_id}'."
                                    )

                                    # delete bucket
                                    try:
                                        if not self._dry_run:
                                            self.client_s3.delete_bucket(
                                                Bucket=resource_id
                                            )
                                    except:
                                        self.logging.error(
                                            f"Could not delete S3 Bucket '{resource_id}'."
                                        )
                                        self.logging.error(sys.exc_info()[1])
                                        resource_action = "ERROR"
                                    else:
                                        self.logging.info(
                                            f"S3 Bucket '{resource_id}' was created {delta.days} days ago "
                                            "and has been deleted."
                                        )
                                        resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"S3 Bucket '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"S3 Bucket '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                self.execution_log.get("AWS").setdefault(self.region, {}).setdefault(
                    "S3", {}
                ).setdefault("Bucket", []).append(
                    {
                        "id": resource_id,
                        "action": resource_action,
                        "timestamp": datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            self.logging.debug("Finished cleanup of S3 Buckets.")
            return True
        else:
            self.logging.info("Skipping cleanup of S3 Buckets.")
            return True
