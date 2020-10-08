import json
import os
import sys
import time

import boto3
from boto3.dynamodb.types import TypeDeserializer


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
    body = []
    client = boto3.client("dynamodb")
    deserializer = TypeDeserializer()

    try:
        resources = client.scan(TableName=os.environ["WHITELISTTABLE"]).get("Items")
        for resource in resources:
            item = {}
            for key, value in resource.items():
                item[key] = str(deserializer.deserialize(value))

                if key == "expiration":
                    # convert EPOCH timestamp to a human readable one
                    item["expiration_human"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(deserializer.deserialize(value)),
                    )

            body.append(item)

        return get_return(200, body)
    except:
        return get_return(400, sys.exc_info()[1])
