import json
import os

import boto3


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
    parameters = event.get("queryStringParameters")

    if parameters.get("resource_id") in (None, ""):
        return get_return(400, "Resource ID cannot be null", parameters, None)

    try:
        boto3.client("dynamodb").delete_item(
            TableName=os.environ.get("ALLOWLIST_TABLE"),
            Key={
                "resource_id": {"S": parameters.get("resource_id")},
            },
        )

        return get_return(
            200,
            f"""Allowlist entry '{parameters.get("resource_id")}' has been deleted""",
            parameters,
            parameters,
        )
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"""Could not delete allowlist entry '{parameters.get("resource_id")}'""",
            parameters,
            None,
        )
