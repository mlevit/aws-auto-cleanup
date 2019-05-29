import datetime
import logging

import moto
import pytest

from .. import dynamodb_cleanup


class TestTablesMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_dynamodb2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = test_class.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        test_class.tables()

        # # validate table deletion
        response = test_class.client_dynamodb.list_tables()
        assert response["TableNames"] == []


class TestTablesLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_dynamodb2():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": 7}}},
            }
            resource_tree = {"AWS": {}}

            test_class = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = test_class.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        test_class.tables()

        # # validate table not deleted
        response = test_class.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]


class TestTablesWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_dynamodb2():
            whitelist = {"dynamodb": {"table": ["settings-table"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"dynamodb": {"tables": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = dynamodb_cleanup.DynamoDBCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_dynamodb.create_table(
            TableName="settings-table",
            KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        # validate table creation
        response = test_class.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]

        # test tables functions
        test_class.tables()

        # # validate table not deleted
        response = test_class.client_dynamodb.list_tables()
        assert "settings-table" in response["TableNames"]
