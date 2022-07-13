import sys
import threading

import boto3

from src.helper import Helper


class S3Cleanup:
    def __init__(self, logging, allowlist, settings, execution_log):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = "global"

        self._client_s3 = None
        self._resource_s3 = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.s3.bucket.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.s3.bucket.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "s3.bucket")
        semaphore = threading.Semaphore(value=5)

        if is_cleaning_enabled:
            try:
                resources = self.client_s3.list_buckets().get("Buckets")
            except:
                self.logging.error("Could not list all S3 Buckets.")
                self.logging.error(sys.exc_info()[1])
                return False

            # threads list
            threads = []

            for resource in resources:
                threads.append(
                    threading.Thread(
                        target=self.delete_bucket,
                        args=(
                            semaphore,
                            resource,
                            resource_allowlist,
                            resource_maximum_age,
                        ),
                    )
                )

            # start all threads
            for thread in threads:
                thread.start()

            # make sure that all threads have finished
            for thread in threads:
                thread.join()

            self.logging.debug("Finished cleanup of S3 Buckets.")
            return True
        else:
            self.logging.info("Skipping cleanup of S3 Buckets.")
            return True

    def delete_bucket(
        self, semaphore, resource, resource_allowlist, resource_maximum_age
    ):
        semaphore.acquire()

        resource_id = resource.get("Name")
        resource_date = resource.get("CreationDate")
        resource_age = Helper.get_day_delta(resource_date).days
        resource_action = None

        if Helper.not_allowlisted(resource_id, resource_allowlist):
            if resource_age > resource_maximum_age:
                # delete bucket policy
                try:
                    if not self.is_dry_run:
                        self.client_s3.delete_bucket_policy(Bucket=resource_id)
                except:
                    self.logging.error(
                        f"Could not delete Bucket Policy for S3 Bucket '{resource_id}'."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    self.logging.debug(
                        f"Deleted Bucket Policy for S3 Bucket '{resource_id}'."
                    )

                    bucket_resource = self.resource_s3.Bucket(resource_id)

                    # delete all objects
                    try:
                        if not self.is_dry_run:
                            bucket_resource.objects.delete()
                    except:
                        self.logging.error(
                            f"Could not delete all Objects from S3 Bucket '{resource_id}'."
                        )
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        self.logging.debug(
                            f"Deleted all Objects from S3 Bucket '{resource_id}'."
                        )

                        # delete all Versions and DeleteMarkers
                        try:
                            if not self.is_dry_run:
                                bucket_resource.object_versions.delete()
                        except:
                            self.logging.error(
                                f"Could not get all Versions and Delete Markers from S3 Bucket '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.debug(
                                f"Deleted all Versions and Delete Markers from S3 Bucket '{resource_id}'."
                            )

                            # delete bucket
                            try:
                                if not self.is_dry_run:
                                    self.client_s3.delete_bucket(Bucket=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete S3 Bucket '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"S3 Bucket '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
            else:
                self.logging.debug(
                    f"S3 Bucket '{resource_id}' was created {resource_age} days ago "
                    "(less than TTL setting) and has not been deleted."
                )
                resource_action = "SKIP - TTL"
        else:
            self.logging.debug(
                f"S3 Bucket '{resource_id}' has been allowlisted and has not been deleted."
            )
            resource_action = "SKIP - ALLOWLIST"

        Helper.record_execution_log_action(
            self.execution_log,
            self.region,
            "S3",
            "Bucket",
            resource_id,
            resource_action,
        )

        semaphore.release()

        return True
