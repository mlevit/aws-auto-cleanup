# Read Settings Resource

Returns a dictionary of each AWS services and resources that are supported by Auto Cleanup.

**URL**: `/settings/resource`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
{
  "message": "string",
  "request": null,
  "response": { "string": ["string"] }
}
```

### Content example

```json
{
  "message": "Supported AWS services and resources list retrieved",
  "request": null,
  "response": {
    "rds": ["instance", "snapshot"],
    "s3": ["bucket"],
    "sagemaker": ["endpoint", "notebook_instance"],
    "elasticbeanstalk": ["application"],
    "glue": ["dev_endpoint"],
    "emr": ["cluster"],
    "kinesis": ["stream"],
    "dynamodb": ["table"],
    "lambda": ["function"],
    "ecs": ["cluster", "service"],
    "iam": ["role"],
    "redshift": ["cluster", "snapshot"],
    "ec2": ["address", "instance", "security_group", "snapshot", "volume"],
    "cloudformation": ["stack"]
  }
}
```
