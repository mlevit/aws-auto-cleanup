# Update Whitelist Entry

Updates an existing whitelist entry into DynamoDB. This is not meant to be used to update the `owner` or `comment` fields, but rather to extend the `expiration` date to ensure the resources are kept alive for longer.

**URL**: `/whitelist/entry`

**Method**: `PUT`

**Auth required**: No

**Permissions required**: None

## Request

```json
{
  "resource_id": "string",
  "expiration": "EPOCH string",
  "owner": "string",
  "comment": "string"
}
```

### Content example

```json
{
  "resource_id": "s3:bucket:my_bucket",
  "expiration": "123456789",
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
    "expiration": "EPOCH string",
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
  "message": "Whitelist entry updated",
  "request": {
    "comment": "Projext X",
    "expiration": "1603010770",
    "owner": "example@email.com",
    "resource_id": "s3:bucket:my_bucket"
  },
  "response": {
    "resource_id": "s3:bucket:my_bucket",
    "expiration": "1603615570",
    "owner": "example@email.com",
    "comment": "Projext X"
  }
}
```

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The new `expiration` field value is computed by using the value from the payload and adding to it the `ttl` value from the Settings table.
