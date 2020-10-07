import json
import os
import sys

import boto3


def lambda_handler(event, context):
    client = boto3.client("dynamodb")

    try:
        response = client.put_item(
            TableName=os.environ["WHITELISTTABLE"],
            Item={
                "resource_id": {"S": event.get("resource_id")},
                "expire_at": {"N": event.get("expire_at")},
                "owner_email": {"S": event.get("owner_email")},
                "comment": {"S": event.get("comment")},
            },
        )

        return {
            "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
        }
    except:
        return {"statusCode": 500, "body": sys.exc_info()[1]}
