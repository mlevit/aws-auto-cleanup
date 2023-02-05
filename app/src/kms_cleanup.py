import sys

import boto3

from src.helper import Helper


class KMSCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_kms = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_kms(self):
        if not self._client_kms:
            self._client_kms = boto3.client("kms", region_name=self.region)
        return self._client_kms

    def run(self):
        self.keys()

    def keys(self):
        """Deletes KMS Keys."""
        self.logging.debug("Started cleanup of KMS Keys.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.kms.key.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.kms.key.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "kms.key")

        if is_cleaning_enabled:
            try:
                paginator = self.client_kms.get_paginator("list_keys")
                resources = paginator.paginate().build_full_result().get("Keys")
            except:
                self.logging.error("Could not list all KMS Keys.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("KeyId")

                describe_response = self.client_kms.describe_key(
                    KeyId=resource_id,
                )

                resource_date = describe_response.get("KeyMetadata").get("CreationDate")
                resource_manager = describe_response.get("KeyMetadata").get(
                    "KeyManager"
                )
                resource_state = describe_response.get("KeyMetadata").get("KeyState")
                resource_age = Helper.get_day_delta(resource_date).days
                resource_action = None

                if resource_manager == "AWS":
                    continue

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_age > resource_maximum_age:
                        if resource_state == "Enabled":
                            try:
                                if not self.is_dry_run:
                                    self.client_kms.schedule_key_deletion(
                                        KeyId=resource_id, PendingWindowInDays=7
                                    )
                            except:
                                self.logging.error(
                                    f"Could not schedule deletion of KMS Key '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"KMS Key '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been scheduled for deletion."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.info(
                                f"KMS Key '{resource_id}' in state '{resource_state}' has not been scheduled for deletion."
                            )
                            resource_action = "SKIP - STATE"
                    else:
                        self.logging.debug(
                            f"KMS Key '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been scheduled for deletion."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"KMS Key '{resource_id}' has been allowlisted and has not been scheduled for deletion."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "KMS",
                    "Key",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of KMS Keys.")
            return True
        else:
            self.logging.info("Skipping cleanup of KMS Keys.")
            return True
