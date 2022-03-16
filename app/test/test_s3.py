import datetime
import logging

import moto
import pytest

from .. import s3_cleanup


class TestBucketsMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_s3():
            allowlist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": -1}}},
            }
            execution_log = {"AWS": {}}

            test_class = s3_cleanup.S3Cleanup(
                logging, allowlist, settings, execution_log
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        test_class.buckets()

        # validate bucket deletion
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"] == []


class TestBucketsLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_s3():
            allowlist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": 5000}}},
            }
            execution_log = {"AWS": {}}

            test_class = s3_cleanup.S3Cleanup(
                logging, allowlist, settings, execution_log
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        test_class.buckets()

        # validate bucket deletion
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"


class TestBucketsAllowlist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_s3():
            allowlist = {"s3": {"bucket": ["test"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {"s3": {"buckets": {"clean": True, "ttl": -1}}},
            }
            execution_log = {"AWS": {}}

            test_class = s3_cleanup.S3Cleanup(
                logging, allowlist, settings, execution_log
            )
            yield test_class

    def test(self, test_class):
        # create test table
        test_class.client_s3.create_bucket(Bucket="test")

        # validate bucket creation
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"

        # test buckets functions
        test_class.buckets()

        # validate bucket deletion
        response = test_class.client_s3.list_buckets()
        assert response["Buckets"][0]["Name"] == "test"
