# Read Settings Resource

Returns a dictionary of each AWS services and resources that are supported by Auto Cleanup.

**URL**: `/settings/resource`

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
  "response": { "services": { "resources": ["string"] } }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **services** (dict) -- The names of AWS services supported by Auto Cleanup.

      - **resources** (list) -- The names of AWS resources supported within the service.

        - _(string)_
