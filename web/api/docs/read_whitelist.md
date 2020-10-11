# Read Whitelist Entries

Returns the entire whitelist table.

**URL**: `/whitelist`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

## Success Response

**Code**: `200 OK`

```json
[
  {
    "resource_id": "[service:resource:id]",
    "expiration": "[epoch timestamp]",
    "owner": "[string]", # optional
    "comment": "[string]" # optional
  }
]
```

### Content example

```json
[
  {
    "resource_id": "s3:bucket:my_bucket",
    "expiration": "123456789",
    "owner": "example@email.com",
    "comment": "Projext X"
  },
  {
    "resource_id": "ec2:instance:i-12345678",
    "expiration": "123456789",
    "owner": "example@email.com",
    "comment": "Projext X"
  }
]
```
