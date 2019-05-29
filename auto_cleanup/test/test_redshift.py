import datetime
import logging

import moto
import pytest

from .. import redshift_cleanup


class TestClustersMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # validate cluster creation
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "test_class123"

        # test clusters functions
        test_class.clusters()

        # validate cluster deletion
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"] == []


class TestClustersLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # validate cluster creation
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "test_class123"

        # test clusters functions
        test_class.clusters()

        # validate cluster not deleted
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "test_class123"


class TestClustersWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {"redshift": {"cluster": ["test_class123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"clusters": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # validate cluster creation
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "test_class123"

        # test clusters functions
        test_class.clusters()

        # validate cluster not deleted
        response = test_class.client_redshift.describe_clusters()
        assert response["Clusters"][0]["ClusterIdentifier"] == "test_class123"


class TestSnapshotsMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="test_class123"
        )

        # validate snapshot creation
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot deletion
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"] == []


class TestSnapshotsLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="test_class123"
        )

        # validate snapshot creation
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot not deleted
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"


class TestSnapshotsWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_redshift():
            whitelist = {"redshift": {"snapshot": ["snapshot123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"redshift": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = redshift_cleanup.RedshiftCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_redshift.create_cluster(
            DBName="test-test_class",
            ClusterIdentifier="test_class123",
            ClusterType="single-node",
            NodeType="ds2.xlarge",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_redshift.create_cluster_snapshot(
            SnapshotIdentifier="snapshot123", ClusterIdentifier="test_class123"
        )

        # validate snapshot creation
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot not deleted
        response = test_class.client_redshift.describe_cluster_snapshots()
        assert response["Snapshots"][0]["SnapshotIdentifier"] == "snapshot123"
