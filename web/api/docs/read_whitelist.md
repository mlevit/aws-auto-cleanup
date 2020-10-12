# Read Whitelist Entries

Returns the entire whitelist table.

**URL**: `/whitelist`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Request Syntax

N/A

## Request Structure

N/A

## Return type

dict

## Returns

### Response Syntax

```json
{
  "message": "string",
  "request": null,
  "response": {
    "whitelist": [
      {
        "resource_id": "string",
        "expiration": "epoch",
        "owner": "string",
        "comment": "string"
      }
    ]
  }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **whitelist** (list) -- List of all whitelist entries.

      - _(dict)_

        - **resource_id** (string) -- Whitelist entry resource ID.

        - **expiration** (epoch) -- Epoch timestamp when the whitelist entry will expire.

        - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

        - **comment** (string) -- Comment associated with the whitelist entry.
