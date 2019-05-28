import datetime
import logging

import moto
import pytest

from .. import cloudformation_cleanup


class TestStacks:
    @pytest.fixture
    def cf(self):
        with moto.mock_cloudformation():
            whitelist = {}
            settings = {
                "general": {"dry_run": False},
                "services": {"cloudformation": {"stacks": {"clean": True, "ttl": 0}}},
            }
            resource_tree = {"AWS": {}}

            cf = cloudformation_cleanup.CloudFormationCleanup(
                logging, whitelist, settings, resource_tree, "ap-southeast-2"
            )
            yield cf

    def test_stack_removal(self, cf):
        # create test stack
        cf.client_cloudformation.create_stack(
            StackName="sample_sqs",
            TemplateBody='{"Resources":{"SQSQueue":{"Type":"AWS::SQS::Queue","Properties":{"QueueName":"test_queue"}}}}',
        )

        # validate stack creation
        response = cf.client_cloudformation.list_stacks()
        assert response["StackSummaries"][0]["StackName"] == "sample_sqs"

        # test stacks functions
        cf.stacks()

        # validate stack deletion
        response = cf.client_cloudformation.list_stacks()

        assert response["StackSummaries"][0]["StackStatus"] == "DELETE_COMPLETE"
