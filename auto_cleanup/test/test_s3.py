import datetime
import logging

import moto
import pytest

from .. import s3_cleanup


class TestBucketsMoreThanTTL:
    @pytest.fixture
    def s3(self):
        with moto.mock_s3():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            s3 = s3_cleanup.S3Cleanup(logging, whitelist, settings, resource_tree)
            yield s3

    def test(self, s3):
        # create test table
        s3.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = s3.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        s3.buckets()

        # validate bucket deletion
        response = s3.client_s3.list_buckets()
        assert response["Buckets"] == []


class TestBucketsLessThanTTL:
    @pytest.fixture
    def s3(self):
        with moto.mock_s3():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": 5000}}},
            }
            resource_tree = {"AWS": {}}

            s3 = s3_cleanup.S3Cleanup(logging, whitelist, settings, resource_tree)
            yield s3

    def test(self, s3):
        # create test table
        s3.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = s3.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        s3.buckets()

        # validate bucket deletion
        response = s3.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"


class TestBucketsWhitelist:
    @pytest.fixture
    def s3(self):
        with moto.mock_s3():
            whitelist = {"s3": {"bucket": ["test"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            s3 = s3_cleanup.S3Cleanup(logging, whitelist, settings, resource_tree)
            yield s3

    def test(self, s3):
        # create test table
        s3.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = s3.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        s3.buckets()

        # validate bucket deletion
        response = s3.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"
