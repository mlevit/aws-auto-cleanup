import csv
import io
import json
import os
import sys
import time

import boto3


def get_return(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    # get route parameter
    run_number = int(event.get("pathParameters").get("number"))

    if run_number in (None, ""):
        return get_return(400, f"Execution number '{run_number}' is invalid.")

    client = boto3.client("s3")

    # get all files in bucket
    response = client.list_objects_v2(
        Bucket=os.environ["EXECUTIONLOGBUCKET"],
    ).get("Contents")

    files = []
    for row in response:
        files.append(row["Key"])

    # sort file names in desc
    files.sort(reverse=True)

    # retrieve file contents
    file_contents = (
        client.get_object(
            Bucket=os.environ["EXECUTIONLOGBUCKET"],
            Key=files[run_number - 1],
        )
        .get("Body")
        .read()
        .decode("utf-8")
    )

    return get_return(200, list(csv.reader(file_contents.splitlines())))
