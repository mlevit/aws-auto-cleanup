# Read Execution Log

Returns executions logs for a particular Auto Cleanup run. Each log is assigned a `{number}` at API runtime. The newest log is assigned `1`, the second newest `2` and so forth.

**URL**: `/execution/{run}`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

## Request Syntax

`{run}`

## Request Structure

- **run** -- **[REQUIRED]** Execution number. The newest log is assigned `1`, the second newest `2` and so forth.

## Return type

dict

## Returns

### Response Syntax

```json
{
  "message": "string",
  "request": { "run": "string" },
  "response": { "header": ["string"], "body": [["string"]] }
}
```

### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (list) -- Response payload.

    - _(dict)_

      - **header** (list) -- List of column headers.

        - _string_

      - **body** (list) -- List of execution log records.

        - _(list)_

          - _string_
