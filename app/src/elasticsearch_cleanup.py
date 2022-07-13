import sys

import boto3

from src.helper import Helper


class ElasticsearchServiceCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticsearch = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_elasticsearch(self):
        if not self._client_elasticsearch:
            self._client_elasticsearch = boto3.client("es", region_name=self.region)
        return self._client_elasticsearch

    def run(self):
        self.domains()

    def domains(self):
        """Deletes Elasticsearch Service Domains."""
        self.logging.debug("Started cleanup of Elasticsearch Service Domains.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.elasticsearch_service.domain.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.elasticsearch_service.domain.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(
            self.allowlist, "elasticsearch_service.domain"
        )

        if is_cleaning_enabled:
            try:
                resources = self.client_elasticsearch.list_domain_names().get(
                    "DomainNames"
                )
            except:
                self.logging.error("Could not list all Elasticsearch Service Domains.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("DomainName")

                try:
                    resource_details = (
                        self.client_elasticsearch.describe_elasticsearch_domain_config(
                            DomainName=resource_id
                        ).get("DomainConfig")
                    )
                except:
                    self.logging.error(
                        f"Could not get Elasticsearch Service Domain '{resource_id}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    resource_action = "ERROR"
                else:
                    resource_date = resource_details.get("ElasticsearchVersion").get(
                        "Status"
                    )["UpdateDate"]
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_elasticsearch.delete_elasticsearch_domain(
                                        DomainName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete Elasticsearch Service Domain '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"Elasticsearch Service Domain '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"Elasticsearch Service Domain '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Elasticsearch Service Domain '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "Elasticsearch Service",
                    "Domain",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of Elasticsearch Service Domains.")
            return True
        else:
            self.logging.info("Skipping cleanup of Elasticsearch Service Domains.")
            return True
