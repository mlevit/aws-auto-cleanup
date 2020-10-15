import json
import os
from datetime import datetime

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
            None,
            None,
        )

    keys = [row["Key"] for row in response]
    keys.sort(reverse=True)

    logs = []
    for key in keys:
        date = datetime.strptime(key[22:41], "%Y_%m_%d_%H_%M_%S")
        logs.append({"key": key, "date": date.strftime("%c")})

    return get_return(200, f"List of execution logs retrieved", None, {"logs": logs})
