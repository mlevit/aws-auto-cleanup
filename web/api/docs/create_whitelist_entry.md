# Create Whitelist Entry

Inserts a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Request

```json
{
  "resource_id": "[service:resource:id]",
  "owner": "[string]", # optional
  "comment": "[string]" # optional
}
```

### Content example

```json
{
  "resource_id": "s3:bucket:my_bucket",
  "owner": "example@email.com", # optional
  "comment": "Projext X" # optional
}
```

## Success Response

**Code**: `200 OK`

```json
[
  {
    "resource_id": "s3:bucket:my_bucket",
    "expiration": "123456789",
    "owner": "example@email.com",
    "comment": "Projext X"
  }
]
```

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The `expiration` field is computed at insert time. Current time + `ttl` from the Settings table are used to compute the value.
