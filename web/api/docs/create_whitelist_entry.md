# Create Whitelist Entry

Inserts a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Request Syntax

```json
{
  "resource_id": "string",
  "owner": "string",
  "comment": "string"
}
```

## Parameters

- **resource_id** (string) -- **[REQUIRED]** The Auto Cleanup ID of the resource in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

- **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

- **comment** (string) -- Comment associated with the whitelist entry.

## Return type

dict

## Returns

### Response Syntax

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

### Response Structure

- _(dict)_

  - **message** (string) -- Message describing the action taken or an error messsage.

  - **expiration** (EPOCH) -- EPOCH timestamp when the whitelist entry will expire.

  - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

  - **comment** (string) -- Comment associated with the whitelist entry.

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The `expiration` field is computed at insert time. Current time + `ttl` from the Settings table are used to compute the value.
