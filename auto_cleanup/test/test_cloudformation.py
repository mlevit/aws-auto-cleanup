import datetime
import logging

import moto
import pytest

from .. import cloudformation_cleanup


class TestStacksMoreThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_cloudformation():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"cloudformation": {"stacks": {"clean": True, "ttl": -1}}},
            }
            resource_tree = {"AWS": {}}

            test_class = cloudformation_cleanup.CloudFormationCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test stack
        test_class.client_cloudformation.create_stack(
            StackName="sample-sqs",
            TemplateBody='{"Resources":{"SQSQueue":{"Type":"AWS::SQS::Queue","Properties":{"QueueName":"test_queue"}}}}',
        )

        # validate stack creation
        response = test_class.client_cloudformation.list_stacks()
        assert response["StackSummaries"][0]["StackName"] == "sample-sqs"

        # test stacks functions
        test_class.stacks()

        # validate stack deletion
        response = test_class.client_cloudformation.list_stacks()

        assert response["StackSummaries"][0]["StackStatus"] == "DELETE_COMPLETE"


class TestStacksLessThanTTL:
    @pytest.fixture
    def test_class(self):
        with moto.mock_cloudformation():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {
                    "cloudformation": {"stacks": {"clean": True, "ttl": 5000}}
                },
            }
            resource_tree = {"AWS": {}}

            test_class = cloudformation_cleanup.CloudFormationCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test stack
        test_class.client_cloudformation.create_stack(
            StackName="sample-sqs",
            TemplateBody='{"Resources":{"SQSQueue":{"Type":"AWS::SQS::Queue","Properties":{"QueueName":"test_queue"}}}}',
        )

        # validate stack creation
        response = test_class.client_cloudformation.list_stacks()
        assert response["StackSummaries"][0]["StackName"] == "sample-sqs"

        # test stacks functions
        test_class.stacks()

        # validate stack not deleted
        response = test_class.client_cloudformation.list_stacks()

        assert response["StackSummaries"][0]["StackStatus"] == "CREATE_COMPLETE"


class TestStacksWhitelist:
    @pytest.fixture
    def test_class(self):
        with moto.mock_cloudformation():
            whitelist = {"cloudformation": {"stack": ["sample-sqs"]}}
            settings = {
                "general": {"dry_run": False},
                "services": {
                    "cloudformation": {"stacks": {"clean": True, "ttl": 5000}}
                },
            }
            resource_tree = {"AWS": {}}

            test_class = cloudformation_cleanup.CloudFormationCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield test_class

    def test(self, test_class):
        # create test stack
        test_class.client_cloudformation.create_stack(
            StackName="sample-sqs",
            TemplateBody='{"Resources":{"SQSQueue":{"Type":"AWS::SQS::Queue","Properties":{"QueueName":"test_queue"}}}}',
        )

        # validate stack creation
        response = test_class.client_cloudformation.list_stacks()
        assert response["StackSummaries"][0]["StackName"] == "sample-sqs"

        # test stacks functions
        test_class.stacks()

        # validate stack not deleted
        response = test_class.client_cloudformation.list_stacks()

        assert response["StackSummaries"][0]["StackStatus"] == "CREATE_COMPLETE"
