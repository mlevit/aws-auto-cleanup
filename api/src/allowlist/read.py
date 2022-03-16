import json
import os
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
    client = boto3.client("dynamodb")
    paginator = client.get_paginator("scan")
    deserializer = TypeDeserializer()

    try:
        body = []
        page_iterator = paginator.paginate(
            TableName=os.environ.get("ALLOWLIST_TABLE"),
        )

        for page in page_iterator:
            for item in page["Items"]:
                record = {}
                for key, value in item.items():
                    record[key] = str(deserializer.deserialize(value))

                body.append(record)

        return get_return(
            200,
            "Allowlist retrieved",
            None,
            {"allowlist": sorted(body, key=itemgetter("resource_id", "expiration"))},
        )
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(400, "Could not retrieve allowlist", None, None)
