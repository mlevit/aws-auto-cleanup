import json
import os
import sys
import time

import boto3


def get_query_results(query):
    client = boto3.client("athena")

    # execute query and retrieve query execution ID
    try:
        execution_id = client.start_query_execution(
            QueryString=query,
            ResultConfiguration={
                "OutputLocation": f"""s3://{os.environ["ATHENARESULTSBUCKET"]}"""
            },
        ).get("QueryExecutionId")
    except:
        print(f"Could not start query '{query}'.")
        return False

    execution_status = "RUNNING"
    execution_details = ""

    # monitor query status, exit when status is not RUNNING or QUEUED
    while execution_status in ("RUNNING", "QUEUED"):
        try:
            response = client.get_query_execution(QueryExecutionId=execution_id)

            execution_status = response.get("QueryExecution").get("Status").get("State")
            execution_details = (
                response.get("QueryExecution").get("Status").get("StateChangeReason")
            )

            # sleep for 1 second so we don't spam the API
            time.sleep(1)
        except:
            print(
                f"[ERROR] Could not retrieve execution log order with error '{execution_details}'."
            )
            return False

    # if query is successful, return results
    if execution_status == "SUCCEEDED":
        response = client.get_query_results(QueryExecutionId=execution_id)

        # convert result into Python dictionary
        return [
            [data.get("VarCharValue") for data in row["Data"]]
            for row in response["ResultSet"]["Rows"]
        ]
    else:
        print(
            f"[ERROR] Could not retrieve execution log order with error '{execution_details}'."
        )
        return False


def lambda_handler(event, context):
    # get route parameter
    parameter = int(event.get("pathParameters").get("number"))

    if parameter is None or parameter < 1:
        return {
            "statusCode": 500,
            "body": f"Execution number '{parameter}' is invalid.",
        }

    # get execution ID based on parameter
    execution_id = get_query_results(
        f"""WITH cte_max 
                 AS (SELECT execution_id, 
                            MAX(timestamp) AS execution_timestamp 
                     FROM   {os.environ["AUTOCLEANUPDATABASE"]}.{os.environ["EXECUTIONLOGTABLE"]} 
                     GROUP  BY execution_id 
                     ORDER  BY MAX(timestamp) DESC), 
                 cte_order 
                 AS (SELECT ROW_NUMBER() OVER () AS execution_order, 
                            execution_id, 
                            execution_timestamp 
                     FROM   cte_max) 
            SELECT * 
            FROM   cte_order 
            WHERE  execution_order = {parameter}"""
    )[1][1]

    # get execution log based on execution ID
    execution_log = get_query_results(
        f"""SELECT * 
            FROM   {os.environ["AUTOCLEANUPDATABASE"]}.{os.environ["EXECUTIONLOGTABLE"]}
            WHERE  execution_id = '{execution_id}'"""
    )

    return {
        "statusCode": 200,
        "body": json.dumps(execution_log),
    }
