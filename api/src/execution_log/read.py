import csv
import json
import os
from urllib.parse import unquote

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
    client = boto3.client("s3")
    parameters = event.get("pathParameters")
    key = unquote(parameters.get("key"))

    if parameters.get("key") in (None, ""):
        return get_return(
            400,
            f"""Key '{parameters.get("key")}' is invalid""",
            parameters,
            None,
        )

    try:
        file_contents = (
            client.get_object(
                Bucket=os.environ.get("EXECUTION_LOG_BUCKET"),
                Key=key,
            )
            .get("Body")
            .read()
            .decode("utf-8")
        )

        body = list(csv.reader(file_contents.splitlines()))
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"Could not read S3 file '{key}'",
            parameters,
            None,
        )

    return get_return(
        200,
        f"Execution log for S3 file '{key}' retrieved",
        parameters,
        {"header": body[0], "body": body[1:None]},
    )
