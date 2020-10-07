import json
import os
import sys

import boto3


def lambda_handler(event, context):
    client = boto3.client("dynamodb")

    try:
        response = client.delete_item(
            TableName=os.environ["WHITELISTTABLE"],
            Key={
                "resource_id": {"S": event.get("resource_id")},
            },
        )

        return {
            "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
        }
    except:
        return {"statusCode": 500, "body": sys.exc_info()[1]}
