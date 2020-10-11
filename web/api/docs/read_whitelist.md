# Read Whitelist Entries

Returns the entire whitelist table.

**URL**: `/whitelist`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
{
  "message": "string",
  "request": null,
  "response": [
    {
      "resource_id": "string",
      "expiration": "EPOCH string",
      "owner": "string",
      "comment": "string"
    }
  ]
}
```

### Content example

```json
{
  "message": "Whitelist retrieved",
  "request": null,
  "response": [
    {
      "comment": "Auto Cleanup production CloudFormation stack",
      "expiration": "99999999999",
      "owner": "example@email.com",
      "resource_id": "cloudformation:stack:auto-cleanup-prod"
    },
    {
      "comment": "Auto Cleanup development CloudFormation stack",
      "expiration": "99999999999",
      "owner": "example@email.com",
      "resource_id": "cloudformation:stack:auto-cleanup-dev"
    }
  ]
}
```
