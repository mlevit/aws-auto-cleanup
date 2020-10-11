import csv
import io
import json
import os
import sys
import time

import boto3


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
    client = boto3.client("s3")
    parameters = event.get("pathParameters")
    run_number = int(parameters.get("number"))

    if run_number in (None, ""):
        return get_return(
            400, f"Execution number '{run_number}' is invalid", parameters, None
        )

    # get all files in bucket
    try:
        response = client.list_objects_v2(
            Bucket=os.environ["EXECUTIONLOGBUCKET"],
        ).get("Contents")
    except:
        return get_return(400, sys.exc_info()[1], parameters, None)

    files = []
    for row in response:
        files.append(row["Key"])

    # sort file names in desc
    files.sort(reverse=True)

    # retrieve file contents
    try:
        file_contents = (
            client.get_object(
                Bucket=os.environ["EXECUTIONLOGBUCKET"],
                Key=files[run_number - 1],
            )
            .get("Body")
            .read()
            .decode("utf-8")
        )
    except:
        return get_return(400, sys.exc_info()[1], parameters, None)

    return get_return(
        200,
        f"Execution log {run_number} retrieved",
        parameters,
        list(csv.reader(file_contents.splitlines())),
    )
