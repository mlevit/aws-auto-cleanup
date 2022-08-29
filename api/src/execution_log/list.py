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
    paginator = client.get_paginator("list_objects_v2")

    logs = []

    try:
        page_iterator = paginator.paginate(
            Bucket=os.environ.get("EXECUTION_LOG_BUCKET"),
        )

        for page in page_iterator:
            for content in page["Contents"]:
                key = content.get("Key")
                date = datetime.strptime(key[22:41], "%Y_%m_%d_%H_%M_%S")

                logs.append({"key": key, "date": date.strftime("%c")})
    except Exception as error:
        print(f"[ERROR] {error}")
        return get_return(
            400,
            f"""Could not list files in S3 Bucket '{os.environ.get("EXECUTION_LOG_BUCKET")}'""",
            None,
            None,
        )

    return get_return(200, "List of execution logs retrieved", None, {"logs": logs})
