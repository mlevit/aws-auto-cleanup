# Read Settings Service

Returns a list AWS services that are supported by Auto Cleanup.

**URL**: `/settings/service`

**Method**: `GET`

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
  "response": { "services": ["string"] }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **services** (list) -- The names of AWS services supported by Auto Cleanup.

      - _(string)_
