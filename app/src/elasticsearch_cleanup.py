import sys

import boto3

from src.helper import Helper


class ElasticsearchServiceCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_elasticsearch = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_elasticsearch(self):
        if not self._client_elasticsearch:
            self._client_elasticsearch = boto3.client("es", region_name=self.region)
        return self._client_elasticsearch

    def run(self):
        self.domains()

    def domains(self):
        """
        Deletes Elasticsearch Service Domains.
        """

        self.logging.debug("Started cleanup of Elasticsearch Service Domains.")

        clean = (
            self.settings.get("services", {})
            .get("elasticsearch", {})
            .get("domain", {})
            .get("clean", False)
        )

        if clean:
            try:
                resources = self.client_elasticsearch.list_domain_names().get(
                    "DomainNames"
                )
            except:
                self.logging.error("Could not list all Elasticsearch Service Domains.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("elasticsearch", {})
                .get("domain", {})
                .get("ttl", 7)
            )

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
                    resource_date = (
                        resource_details.get("ElasticsearchVersion")
                        .get("Status")
                        .get("UpdateDate")
                    )
                    resource_action = None

                    if resource_id not in self.whitelist.get("elasticsearch", {}).get(
                        "domain", []
                    ):
                        delta = Helper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            try:
                                if not self._dry_run:
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
                                    f"Elasticsearch Service Domain '{resource_id}' was last modified {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"Elasticsearch Service Domain '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"Elasticsearch Service Domain '{resource_id}' has been whitelisted and has not been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

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
