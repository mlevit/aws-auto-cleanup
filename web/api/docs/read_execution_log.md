# Read Execution Log

Returns executions logs for a particular Auto Cleanup run. Each log is assigned a `{number}` at API runtime. The newest log is assigned `1`, the second newest `2` and so forth.

**URL**: `/execution/{number}`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
{
  "message": "string",
  "request": { "string": "string" },
  "response": [["string"]]
}
```

### Content example

```json
{
  "message": "Execution log 2 retrieved",
  "request": {
    "number": "2"
  },
  "response": [
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
      "ap-southeast-2",
      "ecs",
      "service",
      "test",
      "delete",
      "2020-10-10 07:23:11",
      "False",
      "5596d8c9-6434-4d65-aa2a-5df457066fea"
    ],
    [
      "AWS",
      "ap-southeast-2",
      "ecs",
      "cluster",
      "airflow-dev",
      "delete",
      "2020-10-10 07:23:11",
      "False",
      "5596d8c9-6434-4d65-aa2a-5df457066fea"
    ]
  ]
}
```

## Notes

- The first list in the the `response` list is the columns header.
