import sys

import boto3

from . import lambda_helper


class S3Cleanup:
    def __init__(self, logging, whitelist, settings, resource_tree):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.resource_tree = resource_tree
        self.region = "global"

        self._client_s3 = None

    @property
    def client_s3(self):
        if not self._client_s3:
            self._client_s3 = boto3.client("s3")
        return self._client_s3

    def run(self):
        self.buckets()

    def buckets(self):
        """
        Deletes Buckets. All Bucket Objects, Versions and Deleted Markers
        are first deleted before the Bucket can be deleted.
        """

        clean = (
            self.settings.get("services", {})
            .get("s3", {})
            .get("buckets", {})
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
                .get("buckets", {})
                .get("ttl", 7)
            )

            for resource in resources.get("Buckets"):
                resource_id = resource.get("Name")
                resource_date = resource.get("CreationDate")

                if resource_id not in self.whitelist.get("s3", {}).get("bucket", []):
                    delta = lambda_helper.LambdaHelper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        if not self.settings.get("general", {}).get("dry_run", True):
                            # delete all objects
                            try:
                                response = self.client_s3.list_objects_v2(
                                    Bucket=resource_id
                                )
                            except:
                                self.logging.error(
                                    f"Could not retrieve all Objects from S3 Bucket '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                            while response.get("KeyCount") > 0:
                                self.logging.debug(
                                    f"S3 Bucket '{resource_id}' has {len(response.get('Contents'))} Objects that have been deleted."
                                )

                                try:
                                    self.client_s3.delete_objects(
                                        Bucket=resource_id,
                                        Delete={
                                            "Objects": [
                                                {"Key": obj.get("Key")}
                                                for obj in response.get("Contents")
                                            ],
                                            "Quiet": True,
                                        },
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete Objects from S3 Bucket '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])

                                response = self.client_s3.list_objects_v2(
                                    Bucket=resource_id
                                )

                            # delete all Versions and DeleteMarkers
                            try:
                                response = self.client_s3.get_paginator(
                                    "list_object_versions"
                                )
                            except:
                                self.logging.error(
                                    f"Could not get all Versions and Delete Markers from S3 Bucket '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                continue

                            delete_list = []

                            for response_object in response.paginate(
                                Bucket=resource_id
                            ):
                                if "DeleteMarkers" in response_object:
                                    for delete_marker in response_object.get(
                                        "DeleteMarkers"
                                    ):
                                        delete_list.append(
                                            {
                                                "Key": delete_marker["Key"],
                                                "VersionId": delete_marker["VersionId"],
                                            }
                                        )

                                if "Versions" in response_object:
                                    for version in response_object["Versions"]:
                                        delete_list.append(
                                            {
                                                "Key": version["Key"],
                                                "VersionId": version["VersionId"],
                                            }
                                        )

                            self.logging.debug(
                                f"S3 Bucket '{resource_id}' has {len(delete_list)} Versions / Delete Markers that have been deleted."
                            )

                            for i in range(0, len(delete_list), 1000):
                                try:
                                    self.client_s3.delete_objects(
                                        Bucket=resource_id,
                                        Delete={
                                            "Objects": delete_list[i : i + 1000],
                                            "Quiet": True,
                                        },
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not delete Versions and Delete Markers from S3 Bucket '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    continue

                            # delete bucket
                            try:
                                self.client_s3.delete_bucket(Bucket=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete Bucket '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])

                        self.logging.info(
                            f"S3 Bucket '{resource_id}' was created {delta.days} days ago "
                            "and has been deleted."
                        )
                    else:
                        self.logging.debug(
                            f"S3 Bucket '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                else:
                    self.logging.debug(
                        f"S3 Bucket '{resource_id}' has been whitelisted and has not been deleted."
                    )

                self.resource_tree.get("AWS").setdefault(self.region, {}).setdefault(
                    "S3", {}
                ).setdefault("Buckets", []).append(resource_id)
            return True
        else:
            self.logging.info("Skipping cleanup of S3 Buckets.")
            return True
