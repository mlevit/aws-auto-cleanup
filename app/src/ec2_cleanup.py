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
        self.security_groups()
        self.snapshots()
        self.volumes()

    def addresses(self):
        """
        Deletes Addresses not allocated to an EC2 Instance.
        """

        self.logging.debug("Started cleanup of EC2 Addresses.")

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.address.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.address.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.address")

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

                if resource_id not in resource_whitelist:
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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.image.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.image.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.image")

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

                if resource_id not in resource_whitelist:
                    resource_age = Helper.get_day_delta(resource_date).days

                    if resource_age > maximum_resource_age:
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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.instance.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.instance.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.instance")

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
                    resource_date = resource.get("LaunchTime")
                    resource_state = resource.get("State").get("Name")
                    resource_action = None

                    if resource_id not in resource_whitelist:
                        resource_age = Helper.get_day_delta(resource_date).days

                        if resource_age > maximum_resource_age:
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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.security_group.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.security_group.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.security_group")

        if is_cleaning_enabled:
            try:
                # help from https://stackoverflow.com/a/41150217
                paginator = self.client_ec2.get_paginator("describe_instances")
                instances = paginator.paginate().build_full_result().get("Reservations")

                paginator = self.client_ec2.get_paginator("describe_security_groups")
                security_groups = paginator.paginate().build_full_result()[
                    "SecurityGroups"
                ]

                instance_security_group_set = set()
                security_group_set = set()

                for reservation in instances:
                    for instance in reservation.get("Instances"):
                        for security_group in instance.get("SecurityGroups"):
                            instance_security_group_set.add(
                                security_group.get("GroupId")
                            )

                for security_group in security_groups:
                    if security_group.get("GroupName") != "default":
                        security_group_set.add(security_group.get("GroupId"))

                resources = security_group_set - instance_security_group_set
            except:
                self.logging.error("Could not retrieve all unused Security Groups.")
                self.logging.error(sys.exc_info()[1])
                return False

            for resource in resources:
                resource_action = None

                if resource not in resource_whitelist:
                    try:
                        if not self.is_dry_run:
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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.snapshot.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.snapshot.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.snapshot")

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

                if resource_id not in resource_whitelist:
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
                            resource_age = Helper.get_day_delta(resource_date).days

                            if resource_age > maximum_resource_age:
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

        is_cleaning_enabled = Helper.get_setting(
            self.settings, "services.ec2.volume.clean", False
        )
        maximum_resource_age = Helper.get_setting(
            self.settings, "services.ec2.volume.ttl", 7
        )
        resource_whitelist = Helper.get_whitelist(self.whitelist, "ec2.volume")

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

                if resource_id not in resource_whitelist:
                    if resource.get("Attachments") == []:
                        resource_age = Helper.get_day_delta(resource_date).days

                        if resource_age > maximum_resource_age:
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
