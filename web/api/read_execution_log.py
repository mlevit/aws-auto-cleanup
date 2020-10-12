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
    run = int(parameters.get("run"))

    if run in (None, "") or run <= 0:
        return get_return(400, f"Execution run '{run}' is invalid", parameters, None)

    # get all files in bucket
    try:
        response = client.list_objects_v2(
            Bucket=os.environ.get("EXECUTIONLOGBUCKET"),
        ).get("Contents")
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"""Could not list files in S3 Bucket '{os.environ.get("EXECUTIONLOGBUCKET")}'""",
            parameters,
            None,
        )

    files = [row["Key"] for row in response]

    if len(files) == 0:
        return get_return(
            404,
            "No execution logs to retrieve",
            parameters,
            {"header": None, "body": None},
        )

    if run > len(files):
        return get_return(
            404,
            f"No execution log for run {run} exist",
            parameters,
            {"header": None, "body": None},
        )

    # sort file names in desc
    files.sort(reverse=True)

    # retrieve file contents
    try:
        file_contents = (
            client.get_object(
                Bucket=os.environ.get("EXECUTIONLOGBUCKET"),
                Key=files[run - 1],
            )
            .get("Body")
            .read()
            .decode("utf-8")
        )

        body = list(csv.reader(file_contents.splitlines()))
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400, f"Could not read S3 file '{files[run - 1]}'", parameters, None
        )

    return get_return(
        200,
        f"Execution log for run {run} retrieved",
        parameters,
        {"header": body[0], "body": body[1:None]},
    )
