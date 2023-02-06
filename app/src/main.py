import csv
import datetime
import json
import logging
import os
import sys
import tempfile
import threading
from collections import defaultdict

import boto3
from dynamodb_json import json_util as dynamodb_json
from func_timeout import func_set_timeout, FunctionTimedOut

from src.airflow_cleanup import AirflowCleanup
from src.amplify_cleanup import AmplifyCleanup
from src.cloudformation_cleanup import CloudFormationCleanup
from src.cloudwatch_cleanup import CloudWatchCleanup
from src.dynamodb_cleanup import DynamoDBCleanup
from src.ec2_cleanup import EC2Cleanup
from src.ecr_cleanup import ECRCleanup
from src.ecs_cleanup import ECSCleanup
from src.efs_cleanup import EFSCleanup
from src.eks_cleanup import EKSCleanup
from src.elasticache_cleanup import ElastiCacheCleanup
from src.elasticbeanstalk_cleanup import ElasticBeanstalkCleanup
from src.elasticsearch_cleanup import ElasticsearchServiceCleanup
from src.elb_cleanup import ELBCleanup
from src.emr_cleanup import EMRCleanup
from src.glue_cleanup import GlueCleanup
from src.helper import Helper
from src.iam_cleanup import IAMCleanup
from src.kafka_cleanup import KafkaCleanup
from src.kinesis_cleanup import KinesisCleanup
from src.kms_cleanup import KMSCleanup
from src.lambda_cleanup import LambdaCleanup
from src.rds_cleanup import RDSCleanup
from src.redshift_cleanup import RedshiftCleanup
from src.s3_cleanup import S3Cleanup
from src.sagemaker_cleanup import SageMakerCleanup
from src.transfer_cleanup import TransferCleanup


class Cleanup:
    def __init__(self, logging):
        self.logging = logging

        # insert default values into settings and allowlist tables
        self.setup_dynamodb()

        # create dictionaries and variables
        self.execution_log = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )
        self.settings = self.get_settings()
        self.allowlist = self.get_allowlist()
        self.dry_run = Helper.get_setting(self.settings, "general.dry_run", True)

    @func_set_timeout(840)
    def run_cleanup(self):
        if self.dry_run:
            self.logging.info("Auto Cleanup started in DRY RUN mode.")
        else:
            self.logging.info(f"Auto Cleanup started in DESTROY mode.")

        for region in sorted(self.settings.get("regions")):
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
                cloudformation_class = CloudFormationCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                cloudformation_class.run()

                # Managed Workflows for Apache Airflow (MWAA)
                airflow_class = AirflowCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=airflow_class.run, args=()))

                # Amplify
                amplify_class = AmplifyCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=amplify_class.run, args=()))

                # CloudWatch
                cloudwatch_class = CloudWatchCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=cloudwatch_class.run, args=()))

                # DynamoDB
                dynamodb_class = DynamoDBCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=dynamodb_class.run, args=()))

                # ECR
                ecr_class = ECRCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=ecr_class.run, args=()))

                # ECS
                ecs_class = ECSCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=ecs_class.run, args=()))

                # EFS
                efs_class = EFSCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=efs_class.run, args=()))

                # Elastic Beanstalk
                elasticbeanstalk_class = ElasticBeanstalkCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(
                    threading.Thread(target=elasticbeanstalk_class.run, args=())
                )

                # ElastiCache
                elasticache_class = ElastiCacheCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=elasticache_class.run, args=()))

                # Elasticsearch Service
                elasticsearch_class = ElasticsearchServiceCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(
                    threading.Thread(target=elasticsearch_class.run, args=())
                )

                # ELB
                elb_class = ELBCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=elb_class.run, args=()))

                # EKS
                eks_class = EKSCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=eks_class.run, args=()))

                # EMR
                emr_class = EMRCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=emr_class.run, args=()))

                # Glue
                glue_class = GlueCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=glue_class.run, args=()))

                # Kafka
                kafka_class = KafkaCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=kafka_class.run, args=()))

                # Kinesis
                kinesis_class = KinesisCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=kinesis_class.run, args=()))

                # KMS
                kms_class = KMSCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=kms_class.run, args=()))

                # Lambda
                lambda_class = LambdaCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=lambda_class.run, args=()))

                # RDS
                rds_class = RDSCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=rds_class.run, args=()))

                # Redshift
                redshift_class = RedshiftCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=redshift_class.run, args=()))

                # SageMaker
                sagemaker_class = SageMakerCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=sagemaker_class.run, args=()))

                # Transfer
                transfer_class = TransferCleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                threads.append(threading.Thread(target=transfer_class.run, args=()))

                # start all threads
                for thread in threads:
                    thread.start()

                # make sure that all threads have finished
                for thread in threads:
                    thread.join()

                # EC2
                # EC2 will run after most cleanup operations as there is a potential
                # through the removal of other services, EC2 instances will be cleaned up
                ec2_class = EC2Cleanup(
                    self.logging,
                    self.allowlist,
                    self.settings,
                    self.execution_log,
                    region,
                )
                ec2_class.run()
            else:
                self.logging.info(f"Skipping region '{region}'.")

        # global services
        self.logging.info("Switching region to 'global'.")

        # threads list
        threads = []

        # S3
        s3_class = S3Cleanup(
            self.logging, self.allowlist, self.settings, self.execution_log
        )
        threads.append(threading.Thread(target=s3_class.run, args=()))

        # IAM
        # IAM will run after all other cleanup operations as there is a potential
        # through the removal of other services, IAM resources will be freed up
        iam_class = IAMCleanup(
            self.logging, self.allowlist, self.settings, self.execution_log
        )
        threads.append(threading.Thread(target=iam_class.run, args=()))

        # start all threads
        for thread in threads:
            thread.start()

        # make sure that all threads have finished
        for thread in threads:
            thread.join()

        self.logging.info("Auto Cleanup completed.")
        return True

    def get_settings(self):
        settings = {}

        try:
            paginator = boto3.client("dynamodb").get_paginator("scan")
            items = (
                paginator.paginate(TableName=os.environ.get("SETTINGS_TABLE"))
                .build_full_result()
                .get("Items")
            )
        except:
            self.logging.error(
                f"""Could not read DynamoDB table '{os.environ.get("SETTINGS_TABLE")}'."""
            )
            self.logging.error(sys.exc_info()[1])
        else:
            for item in items:
                item_json = dynamodb_json.loads(item, True)
                settings[item_json.get("key")] = item_json.get("value")

        return settings

    def get_allowlist(self):
        allowlist = defaultdict(lambda: defaultdict(set))

        try:
            paginator = boto3.client("dynamodb").get_paginator("scan")
            items = (
                paginator.paginate(TableName=os.environ.get("ALLOWLIST_TABLE"))
                .build_full_result()
                .get("Items")
            )
        except:
            self.logging.error(
                f"""Could not read DynamoDB table '{os.environ.get("ALLOWLIST_TABLE")}'."""
            )
            self.logging.error(sys.exc_info()[1])
        else:
            for item in items:
                item_json = dynamodb_json.loads(item, True)
                parsed_resource_id = Helper.parse_resource_id(
                    item_json.get("resource_id")
                )

                allowlist[parsed_resource_id["service"]][
                    parsed_resource_id["resource_type"]
                ].add(parsed_resource_id["resource"])

        return allowlist

    def setup_dynamodb(self):
        """
        Inserts all the default settings and allowlist data
        into their respective DynamoDB tables. Records will be
        skipped if they already exist in the table.
        """
        try:
            client = boto3.client("dynamodb")

            with open("./src/data/auto-cleanup-settings.json") as settings_data:
                settings_json = json.loads(settings_data.read())

            with open("./src/data/auto-cleanup-allowlist.json") as allowlist_data:
                allowlist_json = json.loads(allowlist_data.read())

            update_settings = False

            # get current settings version
            current_version = client.get_item(
                TableName=os.environ.get("SETTINGS_TABLE"),
                Key={"key": {"S": "version"}},
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
                        f"""to version {new_version} in DynamoDB Table '{os.environ.get("SETTINGS_TABLE")}'."""
                    )
                else:
                    self.logging.debug(
                        f"Existing settings are at the lastest version {current_version} in "
                        f"""DynamoDB Table '{os.environ.get("SETTINGS_TABLE")}'."""
                    )
            else:
                update_settings = True
                self.logging.info(
                    f"""Settings are being inserted into DynamoDB Table '{os.environ.get("SETTINGS_TABLE")}' for the first time."""
                )

            if update_settings:
                for setting in settings_json:
                    try:
                        client.put_item(
                            TableName=os.environ.get("SETTINGS_TABLE"), Item=setting
                        )
                    except:
                        self.logging.error(sys.exc_info()[1])
                        continue

            for allowlist in allowlist_json:
                try:
                    client.put_item(
                        TableName=os.environ.get("ALLOWLIST_TABLE"), Item=allowlist
                    )
                except:
                    self.logging.error(sys.exc_info()[1])
                    continue
        except:
            self.logging.error(sys.exc_info()[1])

    def export_execution_log(self, execution_log, aws_request_id):
        """Export a CSV file with all execution logs during run."""
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
                                                    action.get("id"),
                                                    action.get("action"),
                                                    action.get("timestamp"),
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
                bucket = os.environ.get("EXECUTION_LOG_BUCKET")
                key = f"""{now.strftime("%Y")}/{now.strftime("%m")}/execution_log_{now.strftime("%Y_%m_%d_%H_%M_%S")}.csv"""

                try:
                    client.upload_file(temp_file, bucket, key)
                except:
                    self.logging.error(
                        f"Could not upload the execution log to S3 's3://{bucket}/{key}."
                    )
                    return False
                else:
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
        level=os.environ.get("LOG_LEVEL", "WARNING").upper(),
    )

    # create instance of class
    cleanup = Cleanup(logging)

    try:
        cleanup.run_cleanup()
    except FunctionTimedOut:
        logging.warning(
            "Auto Cleanup execution has exceeded 14 minutes and has been stopped."
        )

    cleanup.export_execution_log(cleanup.execution_log, context.aws_request_id)
