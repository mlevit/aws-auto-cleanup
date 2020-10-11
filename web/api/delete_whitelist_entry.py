import json
import os
import sys

import boto3


def get_return(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    client = boto3.client("dynamodb")
    parameters = event.get("queryStringParameters")

    if parameters.get("resource_id") in (None, ""):
        return get_return(400, "Resource ID cannot be null.")

    try:
        response = client.delete_item(
            TableName=os.environ["WHITELISTTABLE"],
            Key={
                "resource_id": {"S": parameters.get("resource_id")},
            },
        )

        return get_return(
            response["ResponseMetadata"]["HTTPStatusCode"],
            {"resource_id": parameters.get("resource_id")},
        )
    except:
        return get_return(400, sys.exc_info()[1])
