import json
import os
import sys
import time

import boto3
from boto3.dynamodb.types import TypeDeserializer


def get_return(code, message, request, response):
    return {
        "statusCode": code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(
            {"message": message, "request": request, "response": response}
        ),
    }


def lambda_handler(event, context):
    client = boto3.client("dynamodb")
    deserializer = TypeDeserializer()

    try:
        body = []
        resources = client.scan(TableName=os.environ["WHITELISTTABLE"]).get("Items")
        for resource in resources:
            item = {}
            for key, value in resource.items():
                item[key] = str(deserializer.deserialize(value))

            body.append(item)

        return get_return(200, "Whitelist retrieved", None, body)
    except:
        return get_return(400, sys.exc_info()[1], None, None)
