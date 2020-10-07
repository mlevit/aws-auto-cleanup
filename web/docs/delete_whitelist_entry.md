# Delete Whitelist Entry

Deletes a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `DELETE`

**Auth required**: No

**Permissions required**: None

## Request

```json
{
  "resource_id": "[service:resource:id]"
}
```

**Content example**

```json
{
  "resource_id": "s3:bucket:my_bucket"
}
```

## Success Response

**Code**: `200 OK`
