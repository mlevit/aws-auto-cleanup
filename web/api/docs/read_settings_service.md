# Read Settings Service

Returns a list AWS services that are supported by Auto Cleanup.

**URL**: `/settings/service`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
{
  "message": "string",
  "request": null,
  "response": ["string"]
}
```

### Content example

```json
{
  "message": "Supported AWS services and resources list retrieved",
  "request": null,
  "response": [
    "cloudformation",
    "dynamodb",
    "ec2",
    "ecs",
    "elasticbeanstalk",
    "emr",
    "glue",
    "iam",
    "kinesis",
    "lambda",
    "rds",
    "redshift",
    "s3",
    "sagemaker"
  ]
}
```
