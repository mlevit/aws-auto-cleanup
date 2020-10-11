# Update Whitelist Entry

Updates an existing whitelist entry into DynamoDB. This is not meant to be used to update the `owner` or `comment` fields, but rather to extend the `expiration` date to ensure the resources are kept alive for longer.

**URL**: `/whitelist/entry`

**Method**: `PUT`

**Auth required**: No

**Permissions required**: None

## Request

```json
{
  "resource_id": "[service:resource:id]",
  "expiration": "[epoch timestamp]",
  "owner": "[string]", # optional
  "comment": "[string]" # optional
}
```

### Content example

```json
{
  "resource_id": "s3:bucket:my_bucket",
  "expiration": "123456789",
  "owner": "example@email.com",
  "# optional""comment": "Projext X"
}
```

## Success Response

**Code**: `200 OK`

{
"resource_id": "s3:bucket:my_bucket",
"expiration": "123456789",
"owner": "example@email.com",
"# optional""comment": "Projext X"
}

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The new `expiration` field value is computed by using the value from the payload and adding to it the `ttl` value from the Settings table.
