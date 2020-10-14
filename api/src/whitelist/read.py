import json
import os
import time
from operator import itemgetter

import boto3
from boto3.dynamodb.types import TypeDeserializer


def get_return(code, message, request, response):
    return {
        "statusCode": code,
        "headers": {
            "Access-Control-Allow-Credentials": True,
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
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

        return get_return(
            200,
            "Whitelist retrieved",
            None,
            {"whitelist": sorted(body, key=itemgetter("resource_id", "expiration"))},
        )
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(400, "Could not retrieve whitelist", None, None)
