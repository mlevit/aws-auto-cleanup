# AWS Auto Cleanup API

## Table of contents

- [Whitelist](#whitelist)
  - [Create Whitelist Entry](#create-whitelist-entry)
  - [Read Whitelist](#read-whitelist)
  - [Update Whitelist Entry](#update-whitelist-entry)
  - [Delete Whitelist Entry](#delete-whitelist-entry)
- [Execution Log](#execution-log)
  - [Read Execution Log](#read-execution-log)
- [Settings](#settings)
  - [Read Settings Service](#read-settings-service)
  - [Read Settings Resource](#read-settings-resource)

## Whitelist

### Create Whitelist Entry

Inserts a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

```json
{
  "resource_id": "string",
  "owner": "string",
  "comment": "string"
}
```

#### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

  - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

  - **comment** (string) -- Comment associated with the whitelist entry.

#### Return type

dict

#### Returns

##### Response Syntax

```json
{
  "message": "string",
  "request": {
    "resource_id": "string",
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

##### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID.

    - **expiration** (epoch) -- Epoch timestamp when the whitelist entry will expire.

    - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

    - **comment** (string) -- Comment associated with the whitelist entry.

#### Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The `expiration` field is computed at insert time. Current time plus `ttl` from the Settings table are used to compute the value.

### Read Whitelist

Returns the entire whitelist table.

**URL**: `/whitelist`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

N/A

#### Request Structure

N/A

#### Return type

dict

#### Returns

##### Response Syntax

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

##### Response Structure

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

### Update Whitelist Entry

Updates an existing whitelist entry into DynamoDB. This is not meant to be used to update the `owner` or `comment` fields, but rather to extend the `expiration` date to ensure the resources are kept alive for longer.

**URL**: `/whitelist/entry`

**Method**: `PUT`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

```json
{
  "resource_id": "string",
  "expiration": "epoch",
  "owner": "string",
  "comment": "string"
}
```

#### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

  - **expiration** (epoch) -- **[REQUIRED]** Epoch timestamp of the existing whitelist entry.

  - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

  - **comment** (string) -- Comment associated with the whitelist entry.

#### Return type

dict

#### Returns

##### Response Syntax

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

##### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID.

    - **expiration** (epoch) -- Extended Epoch timestamp when the whitelist entry will expire.

    - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

    - **comment** (string) -- Comment associated with the whitelist entry.

#### Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The new `expiration` field value is computed by using the value from the payload and adding to it the `ttl` value from the Settings table.

### Delete Whitelist Entry

Deletes a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `DELETE`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

```json
{
  "resource_id": "string"
}
```

#### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

#### Return type

dict

#### Returns

##### Response Syntax

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

##### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID that was deleted.

## Execution Log

### Read Execution Log

Returns executions logs for a particular Auto Cleanup run. Each log is assigned a `{run}` at API runtime. The newest log is assigned `1`, the second newest `2` and so forth.

**URL**: `/execution/{run}`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

`{run}`

#### Request Structure

- **run** -- **[REQUIRED]** Execution number. The newest log is assigned `1`, the second newest `2` and so forth.

#### Return type

dict

#### Returns

##### Response Syntax

```json
{
  "message": "string",
  "request": { "run": "string" },
  "response": { "header": ["string"], "body": [["string"]] }
}
```

##### Response Structure

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

## Settings

### Read Settings Service

Returns a list AWS services that are supported by Auto Cleanup.

**URL**: `/settings/service`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

N/A

#### Request Structure

N/A

#### Return type

dict

#### Returns

##### Response Syntax

```json
{
  "message": "string",
  "request": null,
  "response": { "services": ["string"] }
}
```

##### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **services** (list) -- The names of AWS services supported by Auto Cleanup.

      - _(string)_

### Read Settings Resource

Returns a dictionary of each AWS services and resources that are supported by Auto Cleanup.

**URL**: `/settings/resource`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

#### Request Syntax

N/A

#### Request Structure

N/A

#### Return type

dict

#### Returns

##### Response Syntax

```json
{
  "message": "string",
  "request": null,
  "response": { "services": { "resources": ["string"] } }
}
```

##### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **services** (dict) -- The names of AWS services supported by Auto Cleanup.

      - **resources** (list) -- The names of AWS resources supported within the service.

        - _(string)_