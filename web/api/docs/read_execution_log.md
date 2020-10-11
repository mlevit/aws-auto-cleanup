# Read Execution Log

Returns executions logs for a particular Auto Cleanup run. Each log is assigned a `{number}` at API runtime. The newest log is assigned `1`, the second newest `2` and so forth.

**URL**: `/execution/{number}`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
[["[string]"]]
```

### Content example

```json
[
  [
    "platform",
    "region",
    "service",
    "resource",
    "resource_id",
    "action",
    "timestamp",
    "dry_run_flag",
    "execution_id"
  ],
  [
    "AWS",
    "ap-south-1",
    "CloudFormation",
    "Stack",
    "AutoTag-Collector",
    "delete",
    "2020-10-08 02:51:50.000",
    "true",
    "d84c6d69-a92c-45b9-a11e-dbd01c5a8ddd"
  ]
]
```
