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
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
        }
    except:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
            "body": sys.exc_info()[1],
        }
