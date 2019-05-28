import datetime
import logging

import moto
import pytest

from .. import redshift_cleanup


class TestClustersMoreThanTTL:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test table
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # print(redshift.client_redshift.describe_clusters())

        # validate table creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate table deletion
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"] == []


class TestClustersLessThanTTL:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test table
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # print(redshift.client_redshift.describe_clusters())

        # validate table creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate table deletion
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"


class TestClustersWhitelist:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {"redshift": {"cluster": ["redshift123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test table
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # print(redshift.client_redshift.describe_clusters())

        # validate table creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate table deletion
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"
