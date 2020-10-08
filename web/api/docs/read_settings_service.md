# Read Settings Service

Returns a list AWS services that are supported by Auto Cleanup.

**URL**: `/settings/service`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
["[service]", "..."]
```

### Content example

```json
[
  "cloudformation",
  "dynamodb",
  "ec2",
  "elasticbeanstalk",
  "emr",
  "glue",
  "iam",
  "lambda",
  "rds",
  "redshift",
  "s3"
]
```
