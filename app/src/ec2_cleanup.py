import sys

import boto3

from src.helper import Helper


class EC2Cleanup:
    def __init__(self, logging, allowlist, settings, execution_log, region):
        self.logging = logging
        self.allowlist = allowlist
        self.settings = settings
        self.execution_log = execution_log
        self.region = region

        self._client_ec2 = None
        self._client_sts = None
        self._resource_ec2 = None
        self.is_dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @property
    def client_sts(self):
        if not self._client_sts:
            self._client_sts = boto3.client("sts")
        return self._client_sts

    @property
    def account_number(self):
        return self.client_sts.get_caller_identity().get("Account")

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
        self.nat_gateways()
        self.security_groups()
        self.snapshots()
        self.volumes()

    def addresses(self):
        """Deletes Addresses not allocated to an EC2 Instance."""
        self.logging.debug("Started cleanup of EC2 Addresses.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.address.clean", False
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.address")

        if is_cleaning_enabled:
            try:
                resources = self.client_ec2.describe_addresses().get("Addresses")
            except:
                self.logging.error("Could not list all EC2 Addresses.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("AllocationId")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource.get("AssociationId") is None:
                        try:
                            if not self.is_dry_run:
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
                        f"EC2 Address '{resource_id}' has been allowlisted and has not "
                        "been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes Images not allocated to an EC2 Instance."""
        self.logging.debug("Started cleanup of EC2 Images.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.image.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ec2.image.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.image")

        if is_cleaning_enabled:
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

            for resource in resources:
                resource_id = resource.get("ImageId")
                resource_date = resource.get("CreationDate")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    resource_age = Helper.get_day_delta(resource_date).days

                    if resource_age > resource_maximum_age:
                        try:
                            if not self.is_dry_run:
                                self.client_ec2.deregister_image(ImageId=resource_id)
                        except:
                            self.logging.error(
                                f"Could not deregister EC2 Image '{resource_id}'."
                            )
                            self.logging.error(sys.exc_info()[1])
                            resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EC2 Image '{resource_id}' was last modified {resource_age} days ago "
                                "and has been deregistered."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EC2 Image '{resource_id}' was last modified {resource_age} days ago "
                            "(less than TTL setting) and has not been deregistered."
                        )
                        resource_action = "SKIP - TTL"
                else:
                    self.logging.debug(
                        f"EC2 Image '{resource_id}' has been allowlisted and has not "
                        "been deregistered."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.instance.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ec2.instance.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.instance")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ec2.get_paginator("describe_instances")
                reservations = (
                    paginator.paginate().build_full_result().get("Reservations")
                )
            except:
                self.logging.error("Could not list all EC2 Instances.")
                self.logging.error(sys.exc_info()[1])
                return False

            for reservation in reservations:
                for resource in reservation.get("Instances"):
                    resource_id = resource.get("InstanceId")
                    resource_date = self.__get_ec2_launch_time(resource)
                    resource_state = resource.get("State").get("Name")
                    resource_age = Helper.get_day_delta(resource_date).days
                    resource_action = None

                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        if resource_age > resource_maximum_age:
                            if resource_state == "running":
                                try:
                                    if not self.is_dry_run:
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
                                        f"launched {resource_age} days ago and has been stopped."
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
                                            if not self.is_dry_run:
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
                                            if not self.is_dry_run:
                                                self.client_ec2.terminate_instances(
                                                    InstanceIds=[resource_id]
                                                )
                                        except:
                                            self.logging.error(
                                                f"Could not delete Instance EC2 '{resource_id}'."
                                            )
                                            self.logging.error(sys.exc_info()[1])
                                            resource_action = "ERROR"
                                        else:
                                            self.logging.info(
                                                f"EC2 Instance '{resource_id}' in a 'stopped' state was last "
                                                f"launched {resource_age} days ago and has been terminated."
                                            )
                                            resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EC2 Instance '{resource_id}' was created {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.debug(
                            f"EC2 Instance '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

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

    def nat_gateways(self):
        """Deletes NAT Gateways."""
        self.logging.debug("Started cleanup of EC2 NAT Gateways.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.nat_gateway.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ec2.nat_gateway.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.nat_gateway")

        if is_cleaning_enabled:
            try:
                resources = self.client_ec2.describe_nat_gateways().get("NatGateways")
            except:
                self.logging.error("Could not list all EC2 NAT Gateways.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("NatGatewayId")
                resource_date = resource.get("CreateTime")
                resource_state = resource.get("State")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource_state in ("available"):
                        resource_age = Helper.get_day_delta(resource_date).days

                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_ec2.delete_nat_gateway(
                                        NatGatewayId=resource_id
                                    )
                            except:
                                self.logging.error(
                                    f"Could not delete EC2 NAT Gateway '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EC2 NAT Gateway '{resource_id}' was last modified {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EC2 NAT Gateway '{resource_id}' was last modified {resource_age} days ago "
                                "(less than TTL setting) and has not been deleted."
                            )
                            resource_action = "SKIP - TTL"
                    else:
                        self.logging.warn(
                            f"ECS NAT Gateway '{resource_id}' in state '{resource_state}' cannot be deleted."
                        )
                        resource_action = "SKIP - IN USE"
                else:
                    self.logging.debug(
                        f"EC2 NAT Gateway '{resource_id}' has been allowlisted and has not "
                        "been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

                Helper.record_execution_log_action(
                    self.execution_log,
                    self.region,
                    "EC2",
                    "NAT Gateway",
                    resource_id,
                    resource_action,
                )

            self.logging.debug("Finished cleanup of EC2 NAT Gateways.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 NAT Gateways.")
            return True

    def security_groups(self):
        """Deletes Security Groups not attached to an EC2 Instance."""
        self.logging.debug("Started cleanup of EC2 Security Groups.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.security_group.clean", False
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.security_group")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ec2.get_paginator("describe_security_groups")
                resources = paginator.paginate().build_full_result()["SecurityGroups"]
            except:
                self.logging.error("Could not retrieve all unused Security Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("GroupId")
                resource_action = None

                if resource.get("GroupName") != "default":
                    if Helper.not_allowlisted(resource_id, resource_allowlist):
                        try:
                            if not self.is_dry_run:
                                self.client_ec2.delete_security_group(
                                    GroupId=resource_id
                                )
                        except:
                            if "DependencyViolation" in str(sys.exc_info()[1]):
                                self.logging.debug(
                                    f"EC2 Security Group '{resource_id}' has a network association"
                                    "and cannot been deleted without deleting the association first."
                                )
                                resource_action = "SKIP - IN USE"
                            else:
                                self.logging.error(
                                    f"Could not delete EC2 Security Group '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                        else:
                            self.logging.info(
                                f"EC2 Security Group '{resource_id}' has no network associations and has "
                                "been deleted."
                            )
                            resource_action = "DELETE"
                    else:
                        self.logging.debug(
                            f"EC2 Security Group '{resource_id}' has been allowlisted and has not been deleted."
                        )
                        resource_action = "SKIP - ALLOWLIST"

                    Helper.record_execution_log_action(
                        self.execution_log,
                        self.region,
                        "EC2",
                        "Security Group",
                        resource_id,
                        resource_action,
                    )

            self.logging.debug("Finished cleanup of EC2 Security Groups.")
            return True
        else:
            self.logging.info("Skipping cleanup of EC2 Security Groups.")
            return True

    def snapshots(self):
        """Deletes Snapshots not attached to EBS volumes."""
        self.logging.debug("Started cleanup of EC2 Snapshots.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.snapshot.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ec2.snapshot.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.snapshot")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ec2.get_paginator("describe_snapshots")
                resources = (
                    paginator.paginate(
                        OwnerIds=[
                            "self",
                        ]
                    )
                    .build_full_result()
                    .get("Snapshots")
                )
            except:
                self.logging.error("Could not list all EC2 Snapshots.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("SnapshotId")
                resource_date = resource.get("StartTime")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    snapshots_in_use = []
                    try:
                        images = self.client_ec2.describe_images(
                            Owners=[
                                "self",
                            ]
                        ).get("Images")
                    except:
                        self.logging.error("Could not retrieve EC2 Images.")
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
                            resource_age = Helper.get_day_delta(resource_date).days

                            if resource_age > resource_maximum_age:
                                try:
                                    if not self.is_dry_run:
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
                                        f"EC2 Snapshot '{resource_id}' was created {resource_age} days ago "
                                        "and has been deleted."
                                    )
                                    resource_action = "DELETE"
                            else:
                                self.logging.debug(
                                    f"EC2 Snapshot '{resource_id} was created {resource_age} days ago "
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
                        f"EC2 Snapshot '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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
        """Deletes Volumes not attached to an EC2 Instance."""
        self.logging.debug("Started cleanup of EC2 Volumes.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.volume.clean", False
        )
        resource_maximum_age = Helper.get_setting(
            self.settings, "services.ec2.volume.ttl", 7
        )
        resource_allowlist = Helper.get_allowlist(self.allowlist, "ec2.volume")

        if is_cleaning_enabled:
            try:
                paginator = self.client_ec2.get_paginator("describe_volumes")
                resources = paginator.paginate().build_full_result().get("Volumes")
            except:
                self.logging.error("Could not list all EC2 Volumes.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_id = resource.get("VolumeId")
                resource_date = resource.get("CreateTime")
                resource_action = None

                if Helper.not_allowlisted(resource_id, resource_allowlist):
                    if resource.get("Attachments") == []:
                        resource_age = Helper.get_day_delta(resource_date).days

                        if resource_age > resource_maximum_age:
                            try:
                                if not self.is_dry_run:
                                    self.client_ec2.delete_volume(VolumeId=resource_id)
                            except:
                                self.logging.error(
                                    f"Could not delete EC2 Volume '{resource_id}'."
                                )
                                self.logging.error(sys.exc_info()[1])
                                resource_action = "ERROR"
                            else:
                                self.logging.info(
                                    f"EC2 Volume '{resource_id}' was created {resource_age} days ago "
                                    "and has been deleted."
                                )
                                resource_action = "DELETE"
                        else:
                            self.logging.debug(
                                f"EC2 Volume '{resource_id}' was created {resource_age} days ago "
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
                        f"EC2 Volume '{resource_id}' has been allowlisted and has not been deleted."
                    )
                    resource_action = "SKIP - ALLOWLIST"

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

    def __get_ec2_launch_time(self, resource):
        for network_interface in resource.get("NetworkInterfaces"):
            if network_interface.get("Attachment").get("DeviceIndex") == 0:
                return network_interface.get("Attachment").get("AttachTime")

        return resource.get("LaunchTime")
