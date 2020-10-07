import json
import os
import sys

import boto3
from dynamodb_json import json_util as dynamodb_json


def lambda_handler(event, context):
    client = boto3.client("dynamodb")
    settings = get_settings()

    print(settings)

    service, resource, resource_id = event.get("resource_id").split(":")

    print(service, resource, resource_id)

    try:
        response = client.put_item(
            TableName=os.environ["WHITELISTTABLE"],
            Item={
                "resource_id": {"S": event.get("resource_id")},
                "expire_at": {"N": event.get("expire_at")},
                "owner_email": {"S": event.get("owner_email")},
                "comment": {"S": event.get("comment")},
            },
        )

        return {
            "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
        }
    except:
        return {"statusCode": 500, "body": sys.exc_info()[1]}


def get_settings():
    settings = {}
    try:
        for record in boto3.client("dynamodb").scan(
            TableName=os.environ["SETTINGSTABLE"]
        )["Items"]:
            record_json = dynamodb_json.loads(record, True)
            settings[record_json.get("key")] = record_json.get("value")
    except:
        pass

    return settings
