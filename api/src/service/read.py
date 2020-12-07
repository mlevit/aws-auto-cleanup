import json
import os

import boto3
from dynamodb_json import json_util as dynamodb_json


def sort_dict(item):
    """
    Sort nested dict
    https://gist.github.com/gyli/f60f0374defc383aa098d44cfbd318eb
    """
    return {
        k: sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(item.items())
    }


def get_settings():
    settings = {}

    paginator = boto3.client("dynamodb").get_paginator("scan")
    items = (
        paginator.paginate(TableName=os.environ.get("SETTINGS_TABLE"))
        .build_full_result()
        .get("Items")
    )

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
        return get_return(400, "Could not read Auto Cleanup settings.", None, None)

    return get_return(
        200,
        "Supported AWS services list retrieved",
        None,
        sort_dict(settings.get("services")),
    )
