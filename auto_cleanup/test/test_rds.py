import datetime
import logging

import moto
import pytest

from .. import rds_cleanup


class TestSnapshotsMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_rds2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot deletion
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"] == []


class TestSnapshotsLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_rds2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot deletion
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"


class TestSnapshotsWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_rds2():
            whitelist = {"rds": {"snapshot": ["snapshot123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test cluster
        test_class.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        test_class.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        test_class.snapshots()

        # validate snapshot deletion
        response = test_class.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"
