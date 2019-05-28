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

        # validate cluster creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate cluster deletion
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

        # validate cluster creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate cluster not deleted
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

        # validate cluster creation
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"

        # test clusters functions
        redshift.clusters()

        # validate cluster not deleted
        response = redshift.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "redshift123"


class TestSnapshotsMoreThanTTL:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test cluster
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        redshift.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="redshift123"
        )

        # validate snapshot creation
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        redshift.snapshots()

        # validate snapshot deletion
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"] == []


class TestSnapshotsLessThanTTL:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test cluster
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        redshift.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="redshift123"
        )

        # validate snapshot creation
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        redshift.snapshots()

        # validate snapshot not deleted
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"


class TestSnapshotsWhitelist:
    @pytest.fixture
    def redshift(self):
        with moto.mock_redshift():
            whitelist = {"redshift": {"snapshot": ["snapshot123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            redshift = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield redshift

    def test(self, redshift):
        # create test cluster
        redshift.client_redshift.create_cluster(
            DBName="test-redshift",
            ClusterIdentifier="redshift123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        redshift.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="redshift123"
        )

        # validate snapshot creation
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        redshift.snapshots()

        # validate snapshot not deleted
        response = redshift.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"] == []
