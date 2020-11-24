import sys

import boto3

from src.helper import Helper


class EC2Cleanup:
    def __init__(self, logging, whitelist, settings, execution_log, region):
        self.logging = logging
        self.whitelist = whitelist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_ec2 = None
        self._client_sts = None
        self._resource_ec2 = None
        self._dry_run = self.settings.get("general", {}).get("dry_run", True)

    @property
    def client_sts(self):
        if not self._client_sts:
            self._client_sts = boto3.client("sts")
        return self._client_sts

    @property
    def account_number(self):
        return self.client_sts.get_caller_identity()["Account"]

    @property
    def client_ec2(self):
        if not self._client_ec2:
            self._client_ec2 = boto3.client("ec2", region_name=self.region)
        return self._client_ec2

    @property
    def resource_ec2(self):
        if not self._resource_ec2:
            self._resource_ec2 = boto3.resource("ec2", region_name=self.region)
        return self._resource_ec2

    def run(self):
        self.addresses()
        self.images()
        self.instances()
        self.security_groups()
        self.snapshots()
        self.volumes()

    def addresses(self):
        """
        Deletes Addresses not allocated to an EC2 Instance.
        """

        self.logging.debug("Started cleanup of EC2 Addresses.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("address", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ec2.describe_addresses().get("Addresses")
            except:
                self.logging.error("Could not list all EC2 Addresses.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("AllocationId")
                resource_action = None

                if resource_id not in self.whitelist.get("ec2", {}).get("address", []):
                    if resource.get("AssociationId") is None:
                        try:
                            if not self._dry_run:
                                self.client_ec2.release_address(
                                    AllocationId=resource_id
                                )
                        except:
                            self.logging.error(
                                f"Could not release EC2 Address '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EC2 Address '{resource.get('PublicIp')}' is not associated with an EC2 instance and has "
                                "been released."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EC2 Address '{resource_id}' is associated with an EC2 instance and has not "
                            "been deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"EC2 Address '{resource_id}' has been whitelisted and has not "
                        "been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "Address",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EC2 Addresses.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Addresses.")
            return True

    def images(self):
        """
        Deletes Images not allocated to an EC2 Instance.
        """

        self.logging.debug("Started cleanup of EC2 Images.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("image", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ec2.describe_images(
                    Owners=[
                        "self",
                    ]
                ).get("Images")
            except:
                self.logging.error("Could not list all EC2 Images.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ec2", {})
                .get("image", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("ImageId")
                resource_date = resource.get("CreationDate")
                resource_action = None

                if resource_id not in self.whitelist.get("ec2", {}).get("image", []):
                    delta = Helper.get_day_delta(resource_date)

                    if delta.days > ttl_days:
                        try:
                            if not self._dry_run:
                                self.client_ec2.deregister_image(ImageId=resource_id)
                        except:
                            self.logging.error(
                                f"Could not deregister EC2 Image '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EC2 Image '{resource_id}' was last modified {delta.days} days ago "
                                "and has been deregistered."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EC2 Image '{resource_id}' was last modified {delta.days} days ago "
                            "(less than TTL setting) and has not been deregistered."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EC2 Image '{resource_id}' has been whitelisted and has not "
                        "been deregistered."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "Image",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EC2 Images.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Images.")
            return True

    def instances(self):
        """
        Stops running Instances and terminates stopped instances.
        If Instance has termination protection enabled, the protection will
        be first disabled and then the Instance will be terminated.
        """

        self.logging.debug("Started cleanup of EC2 Instances.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("instance", {})
            .get("clean", False)
        )
        if clean:
            try:
                reservations = self.client_ec2.describe_instances().get("Reservations")
            except:
                self.logging.error("Could not list all EC2 Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ec2", {})
                .get("instance", {})
                .get("ttl", 7)
            )

            for reservation in reservations:
                for resource in reservation.get("Instances"):
                    resource_id = resource.get("InstanceId")
                    resource_date = resource.get("LaunchTime")
                    resource_state = resource.get("State").get("Name")
                    resource_action = None

                    if resource_id not in self.whitelist.get("ec2", {}).get(
                        "instance", []
                    ):
                        delta = Helper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            if resource_state == "running":
                                try:
                                    if not self._dry_run:
                                        self.client_ec2.stop_instances(
                                            InstanceIds=[resource_id]
                                        )
                                except:
                                    self.logging.error(
                                        f"Could not stop EC2 Instance '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.info(
                                        f"EC2 Instance '{resource_id}' in a 'running' state was last "
                                        f"launched {delta.days} days ago and has been stopped."
                                    )
                                    resource_action = "STOP"
                            elif resource_state == "stopped":
                                # disable termination protection before terminating the instance
                                try:
                                    resource_protection = (
                                        self.client_ec2.describe_instance_attribute(
                                            Attribute="disableApiTermination",
                                            InstanceId=resource_id,
                                        )
                                        .get("DisableApiTermination")
                                        .get("Value")
                                    )
                                except:
                                    self.logging.error(
                                        f"Could not get if protection for EC2 Instance '{resource_id}' is on."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    if resource_protection:
                                        try:
                                            if not self._dry_run:
                                                self.client_ec2.modify_instance_attribute(
                                                    DisableApiTermination={
                                                        "Value": False
                                                    },
                                                    InstanceId=resource_id,
                                                )
                                        except:
                                            self.logging.error(
                                                f"Could not remove termination protection from EC2 Instance '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            resource_action = "ERROR"
                                        else:
                                            self.logging.debug(
                                                f"EC2 Instance '{resource_id}' had termination protection "
                                                "turned on and now has been turned off."
                                            )

                                    if resource_action != "ERROR":
                                        try:
                                            if not self._dry_run:
                                                self.client_ec2.terminate_instances(
                                                    InstanceIds=[resource_id]
                                                )
                                        except:
                                            self.logging.error(
                                                f"Could not delete Instance EC2 '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                        else:
                                            self.logging.info(
                                                f"EC2 Instance '{resource_id}' in a 'stopped' state was last "
                                                f"launched {delta.days} days ago and has been terminated."
                                            )
                                            resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EC2 Instance '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EC2 Instance '{resource_id}' has been whitelisted and has not been deleted."
                        )
                        resource_action = "SKIP - WHITELIST"

                    Helper.record_execution_log_action(
                        self.execution_log,
                        self.region,
                        "EC2",
                        "Instance",
                        resource_id,
                        resource_action,
                    )

            self.logging.debug("Finished cleanup of EC2 Instances.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Instances.")
            return True

    def security_groups(self):
        """
        Deletes Security Groups not attached to an EC2 Instance.
        """

        self.logging.debug("Started cleanup of EC2 Security Groups.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("security_group", {})
            .get("clean", False)
        )
        if clean:
            try:
                # help from https://stackoverflow.com/a/41150217
                instances = self.client_ec2.describe_instances()
                security_groups = self.client_ec2.describe_security_groups()

                instance_security_group_set = set()
                security_group_set = set()

                for reservation in instances.get("Reservations"):
                    for instance in reservation.get("Instances"):
                        for security_group in instance.get("SecurityGroups"):
                            instance_security_group_set.add(
                                security_group.get("GroupId")
                            )

                for security_group in security_groups.get("SecurityGroups"):
                    if security_group.get("GroupName") != "default":
                        security_group_set.add(security_group.get("GroupId"))

                resources = security_group_set - instance_security_group_set
            except:
                self.logging.error("Could not retrieve all unused Security Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_action = None

                if resource not in self.whitelist.get("ec2", {}).get(
                    "security_group", []
                ):
                    try:
                        if not self._dry_run:
                            self.client_ec2.delete_security_group(GroupId=resource)
                    except:
                        if "DependencyViolation" in str(sys.exc_info()[1]):
                            self.logging.warn(
                                f"EC2 Security Group '{resource}' has a dependent object "
                                "and cannot been deleted without deleting the dependent object first."
                            )
                            resource_action = "SKIP - IN USE"
                        else:
                            self.logging.error(
                                f"Could not delete EC2 Security Group '{resource}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                    else:
                        self.logging.info(
                            f"EC2 Security Group '{resource}' is not associated with an EC2 instance and has "
                            "been deleted."
                        )
                        resource_action = "DELETE"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "Security Group",
                    resource,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EC2 Security Groups.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Security Groups.")
            return True

    def snapshots(self):
        """
        Deletes Snapshots not attached to EBS volumes.
        """

        self.logging.debug("Started cleanup of EC2 Snapshots.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("snapshot", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ec2.describe_snapshots(
                    OwnerIds=[
                        "self",
                    ]
                ).get("Snapshots")
            except:
                self.logging.error("Could not list all EC2 Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ec2", {})
                .get("snapshot", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("SnapshotId")
                resource_date = resource.get("StartTime")
                resource_action = None

                if resource_id not in self.whitelist.get("ec2", {}).get("snapshot", []):
                    snapshots_in_use = []
                    try:
                        images = self.client_ec2.describe_images(
                            Owners=[
                                "self",
                            ]
                        ).get("Images")
                    except:
                        self.logging.error(f"Could not retrieve EC2 Images.")
                        self.logging.error(sys.exc_info()[1])
                        resource_action = "ERROR"
                    else:
                        for image in images:
                            block_device_mappings = image.get("BlockDeviceMappings")

                            for block_device_mapping in block_device_mappings:
                                if "Ebs" in block_device_mapping:
                                    snapshots_in_use.append(
                                        block_device_mapping.get("Ebs").get(
                                            "SnapshotId"
                                        )
                                    )

                        if resource_id not in snapshots_in_use:
                            delta = Helper.get_day_delta(resource_date)

                            if delta.days > ttl_days:
                                try:
                                    if not self._dry_run:
                                        self.client_ec2.delete_snapshot(
                                            SnapshotId=resource_id
                                        )
                                except:
                                    self.logging.error(
                                        f"Could not delete EC2 Snapshot '{resource_id}'."
                                    )
                                    self.logging.error(sys.exc_info()[1])
                                    resource_action = "ERROR"
                                else:
                                    self.logging.info(
                                        f"EC2 Snapshot '{resource_id}' was created {delta.days} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "DELETE"
                            else:
                                self.logging.debug(
                                    f"EC2 Snapshot '{resource_id} was created {delta.days} days ago "
                                    "(less than TTL setting) and has not been deleted."
                                )
                                resource_action = "SKIP - TTL"
                        else:
                            self.logging.debug(
                                f"EC2 Snapshot '{resource_id}' is currently used by an Image "
                                "and cannot been deleted without deleting the Image first."
                            )
                            resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"EC2 Snapshot '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "Snapshot",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EC2 Snapshots.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Snapshots.")
            return True

    def volumes(self):
        """
        Deletes Volumes not attached to an EC2 Instance.
        """

        self.logging.debug("Started cleanup of EC2 Volumes.")

        clean = (
            self.settings.get("services", {})
            .get("ec2", {})
            .get("volume", {})
            .get("clean", False)
        )
        if clean:
            try:
                resources = self.client_ec2.describe_volumes().get("Volumes")
            except:
                self.logging.error("Could not list all EC2 Volumes.")
                self.logging.error(sys.exc_info()[1])
                return False

            ttl_days = (
                self.settings.get("services", {})
                .get("ec2", {})
                .get("volume", {})
                .get("ttl", 7)
            )

            for resource in resources:
                resource_id = resource.get("VolumeId")
                resource_date = resource.get("CreateTime")
                resource_action = None

                if resource_id not in self.whitelist.get("ec2", {}).get("volume", []):
                    if resource.get("Attachments") == []:
                        delta = Helper.get_day_delta(resource_date)

                        if delta.days > ttl_days:
                            try:
                                if not self._dry_run:
                                    self.client_ec2.delete_volume(VolumeId=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete EC2 Volume '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EC2 Volume '{resource_id}' was created {delta.days} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EC2 Volume '{resource_id}' was created {delta.days} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EC2 Volume '{resource_id}' is attached to an EC2 instance "
                            "and has not been deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"EC2 Volume '{resource_id}' has been whitelisted and has not been deleted."
                    )
                    resource_action = "SKIP - WHITELIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "Volume",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Started cleanup of EC2 Volumes.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Volumes.")
            return True
