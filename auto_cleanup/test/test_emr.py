import datetime
import logging

import moto
import pytest

from .. import emr_cleanup


class TestClustersMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # test clusters functions
        test_class.clusters()

        # validate cluster deletion
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "TERMINATED"


class TestClustersLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # test clusters functions
        test_class.clusters()

        # validate cluster not deleted
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "WAITING"


class TestClustersWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # get test_class Cluster ID and add to whitelist
        test_class.whitelist = {"emr": {"cluster": [response["Clusters"][0]["Id"]]}}

        # test clusters functions
        test_class.clusters()

        # validate cluster not deleted
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "WAITING"
