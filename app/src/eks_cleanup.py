import sys

import boto3

from src.helper import Helper


class EKSCleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_eks = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_eks(self):
        if not self._client_eks:
            self._client_eks = boto3.client("eks", region_name=self.region)
        return self._client_eks

    def run(self):
        self.clusters()

    def clusters(self):
        """
        Deletes EKS Clusters.
        """

        self.logging.debug("Started cleanup of EKS Clusters.")

        clean = (
            self.settings.get("services", {})
            .get("eks", {})
            .get("cluster", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_eks.list_clusters().get("clusters")
            except:
                self.logging.error("Could not list all EKS Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("eks", {})
                .get("cluster", {})
                .get("ttl", 7)
            )

            for resource in resources:
                # for each cluster, we must first delete all the Node Groups
                # and Fargate Profiles before deleting the Cluster itself
                self.fargate_profiles(resource)
                self.node_groups(resource)

                try:
                    resource_details = self.client_eks.describe_cluster(
                        name=resource,
                    ).get("cluster")
                except:
                    self.logging.error(
                        f"Could not get EKS Cluster's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    return False

                resource_id = resource_details.get("name")
                resource_date = resource_details.get("createdAt")
                resource_action = None

                if resource_id not in self.whitelist.get("eks", {}).get("cluster", []):
                    list_fargate_profiles = self.client_eks.list_fargate_profiles(
                        clusterName=resource_id,
                    ).get("fargateProfileNames")

                    list_nodegroups = self.client_eks.list_nodegroups(
                        clusterName=resource_id,
                    ).get("nodegroups")

                    delta = Helper.get_day_delta(resource_date)

                    if len(list_fargate_profiles) == 0 and len(list_nodegroups) == 0:
                        if delta.days > ttl_days:
                            try:
                                if not self._dry_run:
                                    self.client_eks.delete_cluster(name=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete EKS Cluster '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EKS Cluster '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EKS Cluster '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EKS Cluster '{resource_id}' is associated with EKS Fargate Profiles or EKS Node Groups and has not been deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"EKS Cluster '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EKS",
                    "Cluster",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EKS Clusters.")
            return True
        else:
            self.logging.info("Skipping cleanup of EKS Clusters.")
            return True

    def fargate_profiles(self, cluster):
        """
        Deletes EKS Fargate Profiles for a Cluster.
        """

        self.logging.debug(
            f"Started cleanup of EKS Fargate Profiles for EKS Cluster {cluster}."
        )

        clean = (
            self.settings.get("services", {})
            .get("eks", {})
            .get("fargate_profile", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_eks.list_fargate_profiles(
                    clusterName=cluster
                ).get("fargateProfileNames")
            except:
                self.logging.error(
                    f"Could not list all EKS Fargate Profiles for EKS Cluster {cluster}."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("eks", {})
                .get("fargate_profile", {})
                .get("ttl", 7)
            )

            for resource in resources:
                try:
                    resource_details = self.client_eks.describe_fargate_profile(
                        clusterName=cluster,
                        fargateProfileName=resource,
                    ).get("fargateProfile")
                except:
                    self.logging.error(
                        f"Could not get EKS Fargate Profile's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    return False

                resource_id = resource_details.get("fargateProfileName")
                resource_date = resource_details.get("createdAt")
                resource_action = None

                if resource_id not in self.whitelist.get("eks", {}).get(
                    "fargate_profile", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_eks.delete_fargate_profile(
                                    clusterName=cluster, fargateProfileName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete EKS Fargate Profile '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EKS Fargate Profile '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EKS Fargate Profile '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EKS Fargate Profile '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EKS",
                    "Fargate Profile",
                    resource_id,
                    resource_action,
                )

            self.logging.debug(
                f"Finished cleanup of EKS Fargate Profiles for EKS Cluster {cluster}."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of EKS Fargate Profiles for EKS Cluster {cluster}."
            )
            return True

    def node_groups(self, cluster):
        """
        Deletes EKS Node Groups for a Cluster.
        """

        self.logging.debug(
            f"Started cleanup of EKS Node Groups for EKS Cluster {cluster}."
        )

        clean = (
            self.settings.get("services", {})
            .get("eks", {})
            .get("node_group", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_eks.list_nodegroups(clusterName=cluster).get(
                    "nodegroups"
                )
            except:
                self.logging.error(
                    f"Could not list all EKS Node Groups for EKS Cluster {cluster}."
                )
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("eks", {})
                .get("node_group", {})
                .get("ttl", 7)
            )

            for resource in resources:
                try:
                    resource_details = self.client_eks.describe_nodegroup(
                        clusterName=cluster,
                        nodegroupName=resource,
                    ).get("nodegroup")
                except:
                    self.logging.error(
                        f"Could not get EKS Node Group's '{resource}' details."
                    )
                    self.logging.error(sys.exc_info()[1])
                    return False

                resource_id = resource_details.get("nodegroupName")
                resource_date = resource_details.get("createdAt")
                resource_action = None

                if resource_id not in self.whitelist.get("eks", {}).get(
                    "nodegroup", []
                ):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_eks.delete_nodegroup(
                                    clusterName=cluster, nodegroupName=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not delete EKS Node Group '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EKS Node Group '{resource_id}' was created {delta.days} days ago "
                                "and has been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EKS Node Group '{resource_id}' was created {delta.days} days ago "
                            "(less than TTL setting) and has not been deleted."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EKS Node Group '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EKS",
                    "Node Group",
                    resource_id,
                    resource_action,
                )

            self.logging.debug(
                f"Finished cleanup of EKS Node Groups for EKS Cluster {cluster}."
            )
            return True
        else:
            self.logging.info(
                f"Skipping cleanup of EKS Node Groups for EKS Cluster {cluster}."
            )
            return True
