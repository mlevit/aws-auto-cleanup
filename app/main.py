import csv
import datetime
import json
import logging
import os
import sys
import tempfile
import threading
import traceback

import boto3

import cloudformation_cleanup
import dynamodb_cleanup
import ec2_cleanup
import ecs_cleanup
import elasticbeanstalk_cleanup
import emr_cleanup
import glue_cleanup
import helper
import iam_cleanup
import kinesis_cleanup
import lambda_cleanup
import rds_cleanup
import redshift_cleanup
import s3_cleanup
import sagemaker_cleanup


class Cleanup:
    def __init__(self, logging):
        self.logging = logging

        # insert default values into settings and whitelist tables
        self.setup_dynamodb()

        # create dictionaries and variables
        self.execution_log = {"AWS": {}}
        self.settings = self.get_settings()
        self.whitelist = self.get_whitelist()
        self.dry_run = self.settings.get("general", {}).get("dry_run", True)

    def run_cleanup(self):
        if self.dry_run:
            self.logging.info(f"Auto Cleanup started in DRY RUN mode.")
        else:
            self.logging.info(f"Auto Cleanup started in DESTROY mode.")

        for region in self.settings.get("regions"):
            if self.settings.get("regions").get(region).get("clean"):
                self.logging.info(f"Switching to '{region}' region.")

                # check if the region is enabled within the account
                try:
                    client_sts = boto3.client("sts", region_name=region)
                    client_sts.get_caller_identity()
                except:
                    self.logging.info(
                        f"Skipping region '{region}' as it is not enabled within the current account."
                    )
                    continue

                # threads list
                threads = []

                # CloudFormation
                # CloudFormation will run before all other cleanup operations as there is a potential
                # through the removal of CloudFormation Stacks, many of the other resource will be removed
                cloudformation_class = cloudformation_cleanup.CloudFormationCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                cloudformation_class.run()

                # DynamoDB
                dynamodb_class = dynamodb_cleanup.DynamoDBCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=dynamodb_class.run, args=())
                threads.append(thread)

                # ECS
                ecs_class = ecs_cleanup.ECSCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=ecs_class.run, args=())
                threads.append(thread)

                # Elastic Beanstalk
                elasticbeanstalk_class = (
                    elasticbeanstalk_cleanup.ElasticBeanstalkCleanup(
                        self.logging,
                        self.whitelist,
                        self.settings,
                        self.execution_log,
                        region,
                    )
                )
                thread = threading.Thread(target=elasticbeanstalk_class.run, args=())
                threads.append(thread)

                # EMR
                emr_class = emr_cleanup.EMRCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=emr_class.run, args=())
                threads.append(thread)

                # Glue
                glue_class = glue_cleanup.GlueCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=glue_class.run, args=())
                threads.append(thread)

                # Kinesis
                kinesis_class = kinesis_cleanup.KinesisCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=kinesis_class.run, args=())
                threads.append(thread)

                # Lambda
                lambda_class = lambda_cleanup.LambdaCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=lambda_class.run, args=())
                threads.append(thread)

                # RDS
                rds_class = rds_cleanup.RDSCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=rds_class.run, args=())
                threads.append(thread)

                # Redshift
                redshift_class = redshift_cleanup.RedshiftCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=redshift_class.run, args=())
                threads.append(thread)

                # SageMaker
                sagemaker_class = sagemaker_cleanup.SageMakerCleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                thread = threading.Thread(target=sagemaker_class.run, args=())
                threads.append(thread)

                # start all threads
                for thread in threads:
                    thread.start()

                # make sure that all threads have finished
                for thread in threads:
                    thread.join()

                # EC2
                # EC2 will run after most cleanup operations as there is a potential
                # through the removal of other services, EC2 instances will be cleaned up
                ec2_class = ec2_cleanup.EC2Cleanup(
                    self.logging,
                    self.whitelist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                ec2_class.run()
            else:
                self.logging.info(f"Skipping region '{region}'.")

        # global services
        self.logging.info("Switching region to 'global'.")

        # S3
        s3_class = s3_cleanup.S3Cleanup(
            self.logging, self.whitelist, self.settings, self.execution_log
        )
        s3_class.run()

        # IAM
        # IAM will run after all other cleanup operations as there is a potential
        # through the removal of other services, IAM resources will be freed up
        iam_class = iam_cleanup.IAMCleanup(
            self.logging, self.whitelist, self.settings, self.execution_log
        )
        iam_class.run()

        self.logging.info("Auto Cleanup completed.")
        return True

    def get_settings(self):
        settings = {}
        try:
            for record in boto3.client("dynamodb").scan(
                TableName=os.environ["SETTINGSTABLE"]
            )["Items"]:
                record_json = helper.Helper.unmarshal_dynamodb_json(record)
                settings[record_json.get("key")] = record_json.get("value")
        except:
            self.logging.error(
                f"Could not read DynamoDB table '{os.environ['SETTINGSTABLE']}'."
            )
            self.logging.error(sys.exc_info()[1])
        return settings

    def get_whitelist(self):
        whitelist = {}
        try:
            for record in boto3.client("dynamodb").scan(
                TableName=os.environ["WHITELISTTABLE"]
            )["Items"]:
                record_json = helper.Helper.unmarshal_dynamodb_json(record)

                try:
                    parsed_resource_id = helper.Helper.parse_resource_id(
                        record_json.get("resource_id")
                    )
                except:
                    self.logging.error(
                        f"""Resource ID '{record_json.get("resource_id")}' is invalid."""
                    )

                whitelist.setdefault(parsed_resource_id.get("service"), {}).setdefault(
                    parsed_resource_id.get("resource_type"), set()
                ).add(parsed_resource_id.get("resource"))
        except:
            self.logging.error(
                f"Could not read DynamoDB table '{os.environ['WHITELISTTABLE']}'."
            )
            self.logging.error(sys.exc_info()[1])
        return whitelist

    def setup_dynamodb(self):
        """
        Inserts all the default settings and whitelist data
        into their respective DynamoDB tables. Records will be
        skipped if they already exist in the table.
        """

        try:
            client = boto3.client("dynamodb")
            settings_data = open("./data/auto-cleanup-settings.json")
            whitelist_data = open("./data/auto-cleanup-whitelist.json")

            settings_json = json.loads(settings_data.read())
            whitelist_json = json.loads(whitelist_data.read())

            update_settings = False

            # get current settings version
            current_version = client.get_item(
                TableName=os.environ["SETTINGSTABLE"],
                Key={"key": {"S": "version"}},
                ConsistentRead=True,
            )

            # get new settings version
            new_version = float(settings_json[0].get("value", {}).get("N", 0.0))

            # check if settings exist and if they're older than current settings
            if "Item" in current_version:
                current_version = float(
                    current_version.get("Item").get("value").get("N")
                )
                if current_version < new_version:
                    update_settings = True
                    self.logging.info(
                        f"Existing settings with version {current_version} are being updated "
                        f"to version {new_version} in DynamoDB Table '{os.environ['SETTINGSTABLE']}'."
                    )
                else:
                    self.logging.debug(
                        f"Existing settings are at the lastest version {current_version} in "
                        f"DynamoDB Table '{os.environ['SETTINGSTABLE']}'."
                    )
            else:
                update_settings = True
                self.logging.info(
                    f"Settings are being inserted into DynamoDB Table '{os.environ['SETTINGSTABLE']}' for the first time."
                )

            if update_settings:
                for setting in settings_json:
                    try:
                        client.put_item(
                            TableName=os.environ["SETTINGSTABLE"], Item=setting
                        )
                    except:
                        self.logging.error(sys.exc_info()[1])
                        continue

            for whitelist in whitelist_json:
                try:
                    client.put_item(
                        TableName=os.environ["WHITELISTTABLE"], Item=whitelist
                    )
                except:
                    self.logging.error(sys.exc_info()[1])
                    continue

            settings_data.close()
            whitelist_data.close()
        except:
            self.logging.error(sys.exc_info()[1])

    def export_execution_log(self, execution_log, aws_request_id):
        """Export a CSV file with all execution logs during run.

        Args:
            execution_log (dict): Dictionary of all execution logs
        """
        try:
            os.chdir(tempfile.gettempdir())

            try:
                _, temp_file = tempfile.mkstemp()

                try:
                    with open(temp_file, "w") as output_file:
                        wr = csv.writer(output_file)

                        # write header
                        wr.writerow(
                            [
                                "platform",
                                "region",
                                "service",
                                "resource",
                                "resource_id",
                                "action",
                                "timestamp",
                                "dry_run_flag",
                                "execution_id",
                            ]
                        )

                        # write each action
                        for platform, platform_dict in execution_log.items():
                            for region, region_dict in platform_dict.items():
                                for service, service_dict in region_dict.items():
                                    for resource in service_dict:
                                        for action in service_dict.get(resource):
                                            wr.writerow(
                                                [
                                                    platform,
                                                    region,
                                                    service,
                                                    resource,
                                                    action["id"],
                                                    action["action"],
                                                    action["timestamp"],
                                                    self.dry_run,
                                                    aws_request_id,
                                                ]
                                            )

                except:
                    self.logging.error("Could not generate execution log.")
                    self.logging.error(sys.exc_info()[1])
                    return False

                now = datetime.datetime.now()
                client = boto3.client("s3")
                bucket = os.environ["EXECUTIONLOGBUCKET"]
                key = f"""{now.strftime("%Y")}/{now.strftime("%m")}/execution_log_{now.strftime("%Y_%m_%d_%H_%M_%S")}.txt"""

                try:
                    client.upload_file(temp_file, bucket, key)
                except:
                    self.logging.error(
                        f"Could not upload the execution log to S3 's3://{bucket}/{key}."
                    )
                    return False

                self.logging.info(
                    f"Execution log has been uploaded to S3 's3://{bucket}/{key}."
                )
            finally:
                os.remove(temp_file)
            return True
        except:
            self.logging.error("Could not generate the execution log.")
            self.logging.error(sys.exc_info()[1])
            return False


def lambda_handler(event, context):
    # enable logging
    root = logging.getLogger()

    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    logging.basicConfig(
        format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
        level=os.environ.get("LOGLEVEL", "WARNING").upper(),
    )

    # create instance of class
    cleanup = Cleanup(logging)

    # run cleanup
    cleanup.run_cleanup()

    # export execution log
    cleanup.export_execution_log(cleanup.execution_log, context.aws_request_id)
