import json
import os
import sys
import time

import boto3


def _unmarshal_value(node):
    if type(node) is not dict:
        return node

    for key, value in node.items():
        key = key.lower()
        if key == "bool":
            return value
        if key == "null":
            return None
        if key == "s":
            return value
        if key == "n":
            if "." in str(value):
                return float(value)
            return int(value)
        if key in ["m", "l"]:
            if key == "m":
                data = {}
                for key1, value1 in value.items():
                    if key1.lower() == "l":
                        data = [_unmarshal_value(n) for n in value1]
                    else:
                        if type(value1) is not dict:
                            return _unmarshal_value(value)
                        data[key1] = _unmarshal_value(value1)
                return data
            data = []
            for item in value:
                data.append(_unmarshal_value(item))
            return data


def unmarshal_dynamodb_json(node):
    data = dict({})
    data["M"] = node
    return _unmarshal_value(data)


def get_settings():
    settings = {}
    try:
        for record in boto3.client("dynamodb").scan(
            TableName=os.environ["SETTINGSTABLE"]
        )["Items"]:
            record_json = unmarshal_dynamodb_json(record)
            settings[record_json.get("key")] = record_json.get("value")
    except:
        pass

    return settings


def lambda_handler(event, context):
    client = boto3.client("dynamodb")
    settings = get_settings()

    try:
        service, resource, resource_id = event.get("resource_id").split(":")
    except:
        return {
            "statusCode": 500,
            "body": f"""Resource ID '{event.get("resource_id")}' is invalid.""",
        }

    if settings.get("services", {}).get(service) is None:
        return {
            "statusCode": 500,
            "body": f"Service '{service}' is invalid.",
        }

    if settings.get("services", {}).get(service, {}).get(resource) is None:
        return {
            "statusCode": 500,
            "body": f"Resource '{resource}' is invalid.",
        }

    if resource_id is None or len(resource_id) == 0:
        return {
            "statusCode": 500,
            "body": f"Resource ID cannot be empty.",
        }

    resource_days = (
        settings.get("services", {}).get(service, {}).get(resource, {}).get("ttl", 7)
    )

    try:
        response = client.put_item(
            TableName=os.environ["WHITELISTTABLE"],
            Item={
                "resource_id": {"S": event.get("resource_id")},
                "expiration": {
                    "N": str(int(event.get("expiration")) + (resource_days * 86400))
                },
                "owner": {"S": event.get("owner")},
                "comment": {"S": event.get("comment")},
            },
        )

        return {
            "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
        }
    except:
        return {"statusCode": 500, "body": sys.exc_info()[1]}
