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
  "[service]": ["list of resources"]
}
```

### Content example

```json
{
  "rds": ["instance", "snapshot"],
  "s3": ["bucket"],
  "elasticbeanstalk": ["application"],
  "lambda": ["function"],
  "iam": ["role"],
  "redshift": ["cluster", "snapshot"],
  "ec2": ["address", "instance", "security_group", "snapshot", "volume"],
  "glue": ["dev_endpoint"],
  "emr": ["cluster"],
  "cloudformation": ["stack"],
  "dynamodb": ["table"]
}
```
