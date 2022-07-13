import sys

import boto3

from src.helper import Helper


class TransferCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_transfer = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_transfer(self):
        if not self._client_transfer:
            self._client_transfer = boto3.client("transfer", region_name=self.region)
        return self._client_transfer

    def run(self):
        self.servers()

    def servers(self):
        """Deletes Transfer Servers."""
        self.logging.debug("Started cleanup of Transfer Servers.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.transfer.server.clean", False
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "transfer.server")

        if is_cleaning_enabled:
            try:
                paginator = self.client_transfer.get_paginator("list_servers")
                resources = paginator.paginate().build_full_result().get("Servers")
            except:
                self.logging.error("Could not list all Transfer Servers.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("ServerId")
                resource_state = resource.get("State")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_state in ("ONLINE", "START_FAILED", "STOP_FAILED"):
                        try:
                            if not self.is_dry_run:
                                self.client_transfer.delete_server(ServerId=resource_id)
                        except:
                            self.logging.error(
                                f"Could not delete Transfer Server '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"Transfer Server '{resource_id}' has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"Transfer Server '{resource_id}' in state '{resource_state}' cannot be deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"Transfer Server '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Transfer",
                    "Server",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Transfer Servers.")
            return True
        else:
            self.logging.info("Skipping cleanup of Transfer Servers.")
            return True
