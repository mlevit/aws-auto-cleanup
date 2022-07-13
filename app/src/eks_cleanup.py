import sys

import boto3

from src.helper import Helper


class EKSCleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_eks = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_eks(self):
        if not self._client_eks:
            self._client_eks = boto3.client("eks", region_name=self.region)
        return self._client_eks

    def run(self):
        self.clusters()

    def clusters(self):
        """Deletes EKS Clusters."""
        self.logging.debug("Started cleanup of EKS Clusters.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.eks.cluster.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.eks.cluster.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "eks.cluster")

        if is_cleaning_enabled:
            try:
                paginator = self.client_eks.get_paginator("list_clusters")
                resources = paginator.paginate().build_full_result().get("clusters")
            except:
                self.logging.error("Could not list all EKS Clusters.")
                self.logging.error(sys.exc_info()[1])
                return False

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
                    resource_action = "ERROR"
                else:
                    resource_id = resource_details.get("name")
                    resource_date = resource_details.get("createdAt")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        paginator = self.client_eks.get_paginator(
                            "list_fargate_profiles"
                        )
                        list_fargate_profiles = (
                            paginator.paginate(clusterName=resource_id)
                            .build_full_result()
                            .get("fargateProfileNames")
                        )

                        paginator = self.client_eks.get_paginator("list_nodegroups")
                        list_nodegroups = (
                            paginator.paginate(clusterName=resource_id)
                            .build_full_result()
                            .get("nodegroups")
                        )

                        if (
                            len(list_fargate_profiles) == 0
                            and len(list_nodegroups) == 0
                        ):
                            if resource_age > resource_maximum_age:
                                try:
                                    if not self.is_dry_run:
                                        self.client_eks.delete_cluster(name=resource_id)
                                except:
                                    self.logging.error(
                                        f"Could not delete EKS Cluster '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.info(
                                        f"EKS Cluster '{resource_id}' was created {resource_age} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "DELETE"
                            else:
                                self.logging.debug(
                                    f"EKS Cluster '{resource_id}' was created {resource_age} days ago "
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
                            f"EKS Cluster '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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
        """Deletes EKS Fargate Profiles for a Cluster."""
        self.logging.debug(
            f"Started cleanup of EKS Fargate Profiles for EKS Cluster {cluster}."
        )

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.eks.fargate_profile.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.eks.fargate_profile.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "eks.fargate_profile")

        if is_cleaning_enabled:
            try:
                paginator = self.client_eks.get_paginator("list_fargate_profiles")
                resources = paginator.paginate(clusterName=cluster).build_full_result()[
                    "fargateProfileNames"
                ]
            except:
                self.logging.error(
                    f"Could not list all EKS Fargate Profiles for EKS Cluster {cluster}."
                )
                self.logging.error(sys.exc_info()[1])
                return False

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
                    resource_action = "ERROR"
                else:
                    resource_id = resource_details.get("fargateProfileName")
                    resource_date = resource_details.get("createdAt")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_eks.delete_fargate_profile(
                                        clusterName=cluster,
                                        fargateProfileName=resource_id,
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete EKS Fargate Profile '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EKS Fargate Profile '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EKS Fargate Profile '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EKS Fargate Profile '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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
        """Deletes EKS Node Groups for a Cluster."""
        self.logging.debug(
            f"Started cleanup of EKS Node Groups for EKS Cluster {cluster}."
        )

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.eks.node_group.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.eks.node_group.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "eks.node_group")

        if is_cleaning_enabled:
            try:
                paginator = self.client_eks.get_paginator("list_nodegroups")
                resources = paginator.paginate(clusterName=cluster).build_full_result()[
                    "nodegroups"
                ]
            except:
                self.logging.error(
                    f"Could not list all EKS Node Groups for EKS Cluster {cluster}."
                )
                self.logging.error(sys.exc_info()[1])
                return False

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
                    resource_action = "ERROR"
                else:
                    resource_id = resource_details.get("nodegroupName")
                    resource_date = resource_details.get("createdAt")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
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
                                    f"EKS Node Group '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EKS Node Group '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EKS Node Group '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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
