# Read Whitelist Entries

Returns the entire whitelist table.

**URL**: `/api/read/`

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
    "expiration_human": "[%Y-%m-%d %H:%M:%S]",
    "owner": "[string]", # optional
    "comment": "[string]" # optional
  }
]
```

**Content example**

```json
[
  {
    "resource_id": "s3:bucket:my_bucket",
    "expiration": "123456789",
    "expiration_human": "1973-11-29 09:33:09",
    "owner": "example@email.com",
    "comment": "Projext X"
  },
  {
    "resource_id": "ec2:instance:i-12345678",
    "expiration": "123456789",
    "expiration_human": "1973-11-29 09:33:09",
    "owner": "example@email.com",
    "comment": "Projext X"
  }
]
```
