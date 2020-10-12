# Delete Whitelist Entry

Deletes a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `DELETE`

**Auth required**: No

**Permissions required**: None

## Request Syntax

```json
{
  "resource_id": "string"
}
```

## Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

## Return type

dict

## Returns

### Response Syntax

```json
{
  "message": "string",
  "request": {
    "resource_id": "string"
  },
  "response": {
    "resource_id": "string"
  }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID that was deleted.
