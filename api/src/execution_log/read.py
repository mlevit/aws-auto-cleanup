import base64
import csv
import json
import os
import zlib
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
        file_body = list(csv.reader(file_contents.splitlines()))
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"Could not read S3 file '{key}'",
            parameters,
            None,
        )

    body = []
    statistics = {"action": {}, "service": {}, "region": {}}

    for row in file_body[1:]:
        # Create smaller body object removing unecessary fields
        body.append(
            [
                row[6],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
            ]
        )

        # Gather statistics, group by's
        statistics["action"][row[5]] = statistics["action"].get(row[5], 0) + 1
        statistics["service"][row[2] + " " + row[3]] = (
            statistics["service"].get(row[2] + " " + row[3], 0) + 1
        )
        statistics["region"][row[1]] = statistics["region"].get(row[1], 0) + 1

    header = ["timestamp", "region", "service", "resource", "id", "action"]
    is_dry_run = True if file_body[1][7] == "True" else False

    # Compress data using zlib if file length is greater than 10,000 rows
    is_compressed = True if len(file_body) > 10000 else False
    body = (
        base64.b64encode(zlib.compress(bytes(json.dumps(body), "utf-8"))).decode(
            "ascii"
        )
        if is_compressed
        else body
    )

    return get_return(
        200,
        f"Execution log for S3 file '{key}' retrieved",
        parameters,
        {
            "header": header,
            "body": body,
            "statistics": statistics,
            "is_compressed": is_compressed,
            "is_dry_run": is_dry_run,
        },
    )
