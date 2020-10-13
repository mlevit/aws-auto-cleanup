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
            {"message": str(message), "request": request, "response": response}
        ),
    }


def lambda_handler(event, context):
    parameters = event.get("queryStringParameters")

    try:
        settings = get_settings()
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400, "Could not read Auto Cleanup settings.", parameters, None
        )

    try:
        service, resource, resource_id = parameters.get("resource_id").split(":")
    except:
        return get_return(
            400,
            f"""Resource ID '{parameters.get("resource_id")}' is invalid""",
            parameters,
            None,
        )

    if settings.get("services", {}).get(service) in (None, ""):
        return get_return(
            400,
            f"Service '{service}' is either invalid or not supported",
            parameters,
            None,
        )

    if settings.get("services", {}).get(service, {}).get(resource) in (None, ""):
        return get_return(
            400,
            f"Resource '{resource}' is either invalid or not supported",
            parameters,
            None,
        )

    if resource_id in (None, ""):
        return get_return(400, "Resource ID cannot be empty", parameters, None)

    if parameters.get("expiration") in (None, ""):
        return get_return(400, "Expiration cannot be empty", parameters, None)

    resource_ttl = (
        settings.get("services", {}).get(service, {}).get(resource, {}).get("ttl", 7)
    )

    try:
        expiration = int(parameters.get("expiration")) + (resource_ttl * 86400)
        response = boto3.client("dynamodb").put_item(
            TableName=os.environ.get("WHITELISTTABLE"),
            Item={
                "resource_id": {"S": parameters.get("resource_id")},
                "expiration": {"N": str(expiration)},
                "owner": {"S": parameters.get("owner")},
                "comment": {"S": parameters.get("comment")},
            },
        )

        return get_return(
            200,
            f"""Whitelist entry '{parameters.get("resource_id")}' has been extended by {resource_ttl} days""",
            parameters,
            {
                "resource_id": parameters.get("resource_id"),
                "expiration": str(expiration),
                "owner": parameters.get("owner"),
                "comment": parameters.get("comment"),
            },
        )
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"""Could not extend whitelist entry '{parameters.get("resource_id")}'""",
            parameters,
            None,
        )
