# Update Whitelist Entry

Updates an existing whitelist entry into DynamoDB. This is not meant to be used to update the `owner` or `comment` fields, but rather to extend the `expiration` date to ensure the resources are kept alive for longer.

**URL**: `/whitelist/entry`

**Method**: `PUT`

**Auth required**: No

**Permissions required**: None

## Request Syntax

```json
{
  "resource_id": "string",
  "expiration": "epoch",
  "owner": "string",
  "comment": "string"
}
```

## Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

  - **expiration** (epoch) -- **[REQUIRED]** Epoch timestamp of the existing whitelist entry.

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
    "expiration": "epoch",
    "owner": "string",
    "comment": "string"
  },
  "response": {
    "resource_id": "string",
    "expiration": "epoch",
    "owner": "string",
    "comment": "string"
  }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID.

    - **expiration** (epoch) -- Extended Epoch timestamp when the whitelist entry will expire.

    - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

    - **comment** (string) -- Comment associated with the whitelist entry.

## Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The new `expiration` field value is computed by using the value from the payload and adding to it the `ttl` value from the Settings table.
