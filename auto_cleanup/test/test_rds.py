import datetime
import logging

import moto
import pytest

from .. import rds_cleanup


class TestSnapshotsMoreThanTTL:
    @pytest.fixture
    def rds(self):
        with moto.mock_rds2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            rds = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield rds

    def test(self, rds):
        # create test cluster
        rds.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        rds.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        rds.snapshots()

        # validate snapshot deletion
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"] == []


class TestSnapshotsLessThanTTL:
    @pytest.fixture
    def rds(self):
        with moto.mock_rds2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            rds = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield rds

    def test(self, rds):
        # create test cluster
        rds.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        rds.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        rds.snapshots()

        # validate snapshot deletion
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"


class TestSnapshotsWhitelist:
    @pytest.fixture
    def rds(self):
        with moto.mock_rds2():
            whitelist = {"rds": {"snapshot": ["snapshot123"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"rds": {"snapshots": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            rds = rds_cleanup.RDSCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield rds

    def test(self, rds):
        # create test cluster
        rds.client_rds.create_db_instance(
            DBName="test",
            DBInstanceIdentifier="test123",
            AllocatedStorage=10,
            DBInstanceClass="db.m4.large",
            Engine="mysql",
            MasterUsername="admin",
            MasterUserPassword="Admin123",
        )

        # create test snapshot
        rds.client_rds.create_db_snapshot(
            DBSnapshotIdentifier="snapshot123", DBInstanceIdentifier="test123"
        )

        # validate snapshot creation
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"

        # test snapshot functions
        rds.snapshots()

        # validate snapshot deletion
        response = rds.client_rds.describe_db_snapshots()
        assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "snapshot123"
