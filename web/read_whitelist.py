import json
import os
import sys
import time

import boto3
from boto3.dynamodb.types import TypeDeserializer


def lambda_handler(event, context):
    body = []
    client = boto3.client("dynamodb")
    deserializer = TypeDeserializer()

    try:
        resources = client.scan(TableName=os.environ["WHITELISTTABLE"]).get("Items")
        for resource in resources:
            item = {}
            for key, value in resource.items():
                if key == "expire_at":
                    # convert EPOCH timestamp to a human readable one
                    item[key] = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(deserializer.deserialize(value)),
                    )
                else:
                    item[key] = deserializer.deserialize(value)

            body.append(item)

        return {"statusCode": 200, "body": json.dumps(body)}
    except:
        return {"statusCode": 500, "body": sys.exc_info()[1]}
