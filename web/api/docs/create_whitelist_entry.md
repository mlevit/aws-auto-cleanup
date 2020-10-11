# Create Whitelist Entry

Inserts a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Request

```json
{
  "resource_id": "string",
  "owner": "string",
  "comment": "string"
}
```

### Content example

```json
{
  "resource_id": "s3:bucket:my_bucket",
  "owner": "example@email.com",
  "comment": "Projext X"
}
```

## Success Response

**Code**: `200 OK`

```json
{
  "message": "string",
  "request": {
    "resource_id": "string",
    "owner": "string",
    "comment": "string"
  },
  "response": {
    "resource_id": "string",
    "expiration": "EPOCH string",
    "owner": "string",
    "comment": "string"
  }
}
```

### Content example

```json
{
  "message": "New whitelist entry created.",
  "request": {
    "resource_id": "s3:bucket:my_bucket",
    "owner": "example@email.com",
    "comment": "Projext X"
  },
  "response": {
    "resource_id": "s3:bucket:my_bucket",
    "expiration": "1603015051",
    "owner": "example@email.com",
    "comment": "Projext X"
  }
}
```

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The `expiration` field is computed at insert time. Current time + `ttl` from the Settings table are used to compute the value.
