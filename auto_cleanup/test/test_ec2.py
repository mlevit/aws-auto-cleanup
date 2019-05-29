import datetime
import logging

import moto
import pytest

from .. import ec2_cleanup


class TestInstancesMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"instances": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.resource_ec2.create_instances(
            ImageId="ami-43a15f3e", MinCount=1, MaxCount=1, InstanceType="t2.micro"
        )

        # validate instance creation
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["ImageId"] == "ami-43a15f3e"

        # test instances functions for running instace
        test_class.instances()

        # # validate instance stopped
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["State"]["Name"] == "stopped"

        # test instances functions for stopped instance
        test_class.instances()

        # # validate instance stopped
        response = test_class.client_ec2.describe_instances()
        assert (
            response["Reservations"][0]["Instances"][0]["State"]["Name"] == "terminated"
        )


class TestInstancesLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"instances": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.resource_ec2.create_instances(
            ImageId="ami-43a15f3e", MinCount=1, MaxCount=1, InstanceType="t2.micro"
        )

        # validate instance creation
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["ImageId"] == "ami-43a15f3e"

        # test instances functions for running instace
        test_class.instances()

        # # validate instance not stopped
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["State"]["Name"] == "running"


class TestInstancesWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"instances": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.resource_ec2.create_instances(
            ImageId="ami-43a15f3e", MinCount=1, MaxCount=1, InstanceType="t2.micro"
        )

        # validate instance creation
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["ImageId"] == "ami-43a15f3e"

        # get instance id and add to whitelist
        test_class.whitelist = {
            "ec2": {
                "instance": [response["Reservations"][0]["Instances"][0]["InstanceId"]]
            }
        }

        # test instances functions for running instace
        test_class.instances()

        # # validate instance not stopped
        response = test_class.client_ec2.describe_instances()
        assert response["Reservations"][0]["Instances"][0]["State"]["Name"] == "running"


class TestSecurityGroupsNotWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"security_groups": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.client_ec2.create_security_group(
            Description="test-security-group", GroupName="test-security-group"
        )

        # validate instance creation
        response = test_class.client_ec2.describe_security_groups()
        assert response["SecurityGroups"][1]["GroupName"] == "test-security-group"

        # test instances functions for running instace
        test_class.security_groups()

        # validate instance stopped
        response = test_class.client_ec2.describe_security_groups()
        for group in response["SecurityGroups"]:
            assert group["GroupName"] != "test-security-group"


class TestSecurityGroupsWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {"ec2": {"security_group": ["test-security-group"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"security_groups": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.client_ec2.create_security_group(
            Description="test-security-group", GroupName="test-security-group"
        )

        # validate instance creation
        response = test_class.client_ec2.describe_security_groups()
        assert response["SecurityGroups"][1]["GroupName"] == "test-security-group"

        # get security group id and add to whitelist
        test_class.whitelist = {
            "ec2": {"security_group": [response["SecurityGroups"][1]["GroupId"]]}
        }

        # test instances functions for running instace
        test_class.security_groups()

        # validate instance stopped
        response = test_class.client_ec2.describe_security_groups()
        assert response["SecurityGroups"][1]["GroupName"] == "test-security-group"


class TestVolumesMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"volumes": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.client_ec2.create_volume(AvailabilityZone="ap-southeast-2a", Size=10)

        # validate instance creation
        response = test_class.client_ec2.describe_volumes()
        assert len(response["Volumes"]) == 1

        # test instances functions for running instace
        test_class.volumes()

        # validate instance stopped
        response = test_class.client_ec2.describe_volumes()
        assert response["Volumes"] == []


class TestVolumesLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"volumes": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.client_ec2.create_volume(AvailabilityZone="ap-southeast-2a", Size=10)

        # validate instance creation
        response = test_class.client_ec2.describe_volumes()
        assert len(response["Volumes"]) == 1

        # test instances functions for running instace
        test_class.volumes()

        # validate instance stopped
        response = test_class.client_ec2.describe_volumes()
        assert len(response["Volumes"]) == 1


class TestVolumesWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_ec2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"ec2": {"volumes": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = ec2_cleanup.EC2Cleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test instance
        test_class.client_ec2.create_volume(AvailabilityZone="ap-southeast-2a", Size=10)

        # validate instance creation
        response = test_class.client_ec2.describe_volumes()
        assert len(response["Volumes"]) == 1

        # get volume id and add to whitelist
        test_class.whitelist = {"ec2": {"volume": [response["Volumes"][0]["VolumeId"]]}}

        # test instances functions for running instace
        test_class.volumes()

        # validate instance stopped
        response = test_class.client_ec2.describe_volumes()
        assert len(response["Volumes"]) == 1
