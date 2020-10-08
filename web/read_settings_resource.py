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

    body = {}

    for service in settings.get("services", {}):
        body[service] = sorted(list(settings.get("services", {}).get(service).keys()))

    return {
        "statusCode": 200,
        "body": json.dumps(body),
    }
