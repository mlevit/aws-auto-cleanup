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
    parameters = event.get("queryStringParameters")
    settings = get_settings()

    try:
        service, resource, resource_id = parameters.get("resource_id").split(":")
    except:
        return get_return(
            400,
            f"""Resource ID '{parameters.get("resource_id")}' is invalid.""",
            parameters,
            None,
        )

    if settings.get("services", {}).get(service) in (None, ""):
        return get_return(
            400,
            f"Service '{service}' is invalid",
            parameters,
            None,
        )

    if settings.get("services", {}).get(service, {}).get(resource) in (None, ""):
        return get_return(
            400,
            f"Resource '{resource}' is invalid",
            parameters,
            None,
        )

    if resource_id in (None, ""):
        return get_return(
            400,
            "Resource ID cannot be empty",
            parameters,
            None,
        )

    resource_ttl = (
        settings.get("services", {}).get(service, {}).get(resource, {}).get("ttl", 7)
    )

    try:
        expiration = int(time.time()) + (resource_ttl * 86400)
        response = client.put_item(
            TableName=os.environ["WHITELISTTABLE"],
            Item={
                "resource_id": {"S": parameters.get("resource_id")},
                "expiration": {"N": str(expiration)},
                "owner": {"S": parameters.get("owner")},
                "comment": {"S": parameters.get("comment")},
            },
        )

        return get_return(
            response["ResponseMetadata"]["HTTPStatusCode"],
            "Whitelist entry created",
            parameters,
            {
                "resource_id": parameters.get("resource_id"),
                "expiration": str(expiration),
                "owner": parameters.get("owner"),
                "comment": parameters.get("comment"),
            },
        )
    except:
        return get_return(400, sys.exc_info()[1], parameters, None)
