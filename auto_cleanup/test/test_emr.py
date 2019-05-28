import datetime
import logging

import moto
import pytest

from .. import emr_cleanup


class TestClustersMoreThanTTL:
    @pytest.fixture
    def emr(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            emr = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield emr

    def test(self, emr):
        # create test cluster
        emr.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # test clusters functions
        emr.clusters()

        # validate cluster deletion
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "TERMINATED"


class TestClustersLessThanTTL:
    @pytest.fixture
    def emr(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            emr = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield emr

    def test(self, emr):
        # create test cluster
        emr.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # test clusters functions
        emr.clusters()

        # validate cluster not deleted
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "WAITING"


class TestClustersWhitelist:
    @pytest.fixture
    def emr(self):
        with moto.mock_emr():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            emr = emr_cleanup.EMRCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield emr

    def test(self, emr):
        # create test cluster
        emr.client_emr.run_job_flow(
            Name="test",
            Instances={
                "MasterInstanceType": "m5.xlarge",
                "SlaveInstanceType": "m5.xlarge",
                "KeepJobFlowAliveWhenNoSteps": True,
            },
        )

        # validate cluster creation
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Name"] == "test"

        # get EMR Cluster ID and add to whitelist
        emr.whitelist = {"emr": {"cluster": [response["Clusters"][0]["Id"]]}}

        # test clusters functions
        emr.clusters()

        # validate cluster not deleted
        response = emr.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "WAITING"
