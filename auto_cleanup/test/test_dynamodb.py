import datetime
import logging

import moto
import pytest

from .. import dynamodb_cleanup


class TestTablesMoreThanTTL:
    @pytest.fixture
    def dd(self):
        with moto.mock_dynamodb2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            dd = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield dd

    def test(self, dd):
        # create test table
        dd.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = dd.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        dd.tables()

        # # validate table deletion
        response = dd.client_dynamodb.list_tables()
        assert response["TableNames"] == []


class TestTablesLessThanTTL:
    @pytest.fixture
    def dd(self):
        with moto.mock_dynamodb2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            dd = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield dd

    def test(self, dd):
        # create test table
        dd.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = dd.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        dd.tables()

        # # validate table not deleted
        response = dd.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]


class TestTablesWhitelist:
    @pytest.fixture
    def dd(self):
        with moto.mock_dynamodb2():
            whitelist = {"dynamodb": {"table": ["settings-table"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            dd = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield dd

    def test(self, dd):
        # create test table
        dd.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = dd.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        dd.tables()

        # # validate table not deleted
        response = dd.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]
