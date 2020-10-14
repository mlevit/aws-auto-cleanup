import json
import os
import sys
import time

import boto3
from dynamodb_json import json_util as dynamodb_json


def get_settings():
    settings = {}

    try:
        items = boto3.client("dynamodb").scan(
            TableName=os.environ.get("SETTINGSTABLE")
        )["Items"]
    except Exception as error:
        raise error
    else:
        for item in items:
            item_json = dynamodb_json.loads(item, True)
            settings[item_json.get("key")] = item_json.get("value")

        return settings


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
    try:
        settings = get_settings()
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400, "Could not read Auto Cleanup settings.", parameters, None
        )

    return get_return(
        200,
        "Supported AWS services list retrieved",
        None,
        {"services": sorted(list(settings.get("services", {}).keys()))},
    )
