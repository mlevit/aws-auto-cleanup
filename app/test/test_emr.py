import datetime
import logging

import moto
import pytest

from .. import emr_cleanup


class TestClustersMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_emr():
            allowlist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            execution_log = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, allowlist, settings, execution_log, "ap-southeast-2"
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
            allowlist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": 7}}},
            }
            execution_log = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, allowlist, settings, execution_log, "ap-southeast-2"
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


class TestClustersAllowlist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_emr():
            allowlist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"emr": {"clusters": {"clean": True, "ttl": -1}}},
            }
            execution_log = {"AWS": {}}

            test_class = emr_cleanup.EMRCleanup(
                logging, allowlist, settings, execution_log, "ap-southeast-2"
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

        # get test_class Cluster ID and add to allowlist
        test_class.allowlist = {"emr": {"cluster": [response["Clusters"][0]["Id"]]}}

        # test clusters functions
        test_class.clusters()

        # validate cluster not deleted
        response = test_class.client_emr.list_clusters()
        assert response["Clusters"][0]["Status"]["State"] == "WAITING"
