import json
import os
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
    deserializer = TypeDeserializer()

    try:
        body = []
        resources = (
            boto3.client("dynamodb")
            .scan(TableName=os.environ.get("WHITELISTTABLE"))
            .get("Items")
        )
        for resource in resources:
            item = {}
            for key, value in resource.items():
                item[key] = str(deserializer.deserialize(value))

            body.append(item)

        return get_return(200, "Whitelist retrieved", None, body)
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(400, "Could not retrieve whitelist", None, None)
