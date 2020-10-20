# AWS Auto Cleanup API

The Auto Cleanup API is a serverless Lambda-based API built to facilitate the website. The architecture diagram below illustrates the various services and their relationships with one another.

**This module is to be deployed second.**

![architecture](./static/architecture.drawio.svg)

## Table of contents

- [Table of contents](#table-of-contents)
- [Deployment](#deployment)
- [Removal](#removal)
- [API](#api)

## Deployment

1. Install [AWS CLI](https://aws.amazon.com/cli/)

   ```bash
   pip install awscli
   ```

2. [Quickly Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration)

   - _Auto Cleanup should be deployed by a user with administrative privileges._

3. Install [Serverless Framework](https://www.serverless.com/)

   ```bash
   npm install -g serverless
   ```

4. Download

   ```bash
   git clone https://github.com/servian/aws-auto-cleanup.git
   ```

5. Change directory

   ```bash
   cd aws-auto-cleanup/api/
   ```

6. Install dependencies

   ```bash
   npm install
   ```

7. Deploy

   ```bash
   npm run deploy -- [--region] [--aws-profile]
   ```

## Removal

1. Change directory

   ```bash
   cd aws-auto-cleanup-api
   ```

2. Remove

   ```bash
   npm run remove -- [--region] [--aws-profile]
   ```

## API

- [Whitelist](#whitelist)
- [Execution Log](#execution-log)
- [Service](#service)

### Whitelist

#### Create

Inserts a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `POST`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

```json
{
  "resource_id": "string",
  "owner": "string",
  "comment": "string"
}
```

##### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

  - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

  - **comment** (string) -- Comment associated with the whitelist entry.

##### Return type

dict

##### Returns

###### Response Syntax

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

###### Response Structure

- _(dict)_

  - **message** (string) -- If the operation was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID.

    - **expiration** (epoch) -- Epoch timestamp when the whitelist entry will expire.

    - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

    - **comment** (string) -- Comment associated with the whitelist entry.

##### Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The `expiration` field is computed at insert time. Current time plus `ttl` from the Settings table are used to compute the value.

#### Read

Returns the entire whitelist table.

**URL**: `/whitelist`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

N/A

##### Request Structure

N/A

##### Return type

dict

##### Returns

###### Response Syntax

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

###### Response Structure

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

#### Update

Updates an existing whitelist entry into DynamoDB. This is not meant to be used to update the `owner` or `comment` fields, but rather to extend the `expiration` date to ensure the resources are kept alive for longer.

**URL**: `/whitelist/entry`

**Method**: `PUT`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

```json
{
  "resource_id": "string",
  "expiration": "epoch",
  "owner": "string",
  "comment": "string"
}
```

##### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

  - **expiration** (epoch) -- **[REQUIRED]** Epoch timestamp of the existing whitelist entry.

  - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

  - **comment** (string) -- Comment associated with the whitelist entry.

##### Return type

dict

##### Returns

###### Response Syntax

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

###### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID.

    - **expiration** (epoch) -- Extended Epoch timestamp when the whitelist entry will expire.

    - **owner** (string) -- The name or email address belonging to the owner of the whitelist entry.

    - **comment** (string) -- Comment associated with the whitelist entry.

##### Notes

- AWS service (e.g. `s3`) and resource (e.g. `bucket`) will be evaluated against the Settings table to ensure they are valid.

- The new `expiration` field value is computed by using the value from the payload and adding to it the `ttl` value from the Settings table.

#### Delete

Deletes a new whitelist entry into DynamoDB.

**URL**: `/whitelist/entry`

**Method**: `DELETE`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

```json
{
  "resource_id": "string"
}
```

##### Request Structure

- _(dict)_

  - **resource_id** (string) -- **[REQUIRED]** Unique resource ID in format `service:resource:id`. For a list of acceptable values, [see this table](https://github.com/servian/aws-auto-cleanup#whitelist).

##### Return type

dict

##### Returns

###### Response Syntax

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

###### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - **resource_id** (string) -- Whitelist entry resource ID that was deleted.

### Execution Log

#### List

Returns a list of all Auto Cleanup App executions in descending order

**URL**: `/execution`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

N/A

##### Request Structure

N/A

##### Return type

dict

##### Returns

###### Response Syntax

```json
{
  "message": "string",
  "request": null,
  "response": { "logs": [{ "key": "string", "date": "string" }] }
}
```

###### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (list) -- Response payload.

    - **logs** (list) -- List of all execution logs.

      - _(dict)_

        - **key** (string) -- S3 key.

        - **date** (string) -- Locale’s appropriate date and time representation.

#### Read

Returns executions logs for a particular Auto Cleanup execution log S3 key.

**URL**: `/execution/{key}`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

`{key}`

##### Request Structure

- **key** -- **[REQUIRED]** S3 key, URL encoded.

##### Return type

dict

##### Returns

###### Response Syntax

```json
{
  "message": "string",
  "request": { "key": "string" },
  "response": { "header": ["string"], "body": [["string"]] }
}
```

###### Response Structure

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

### Service

#### Read

Returns a list AWS services that are supported by Auto Cleanup.

**URL**: `/settings/service`

**Method**: `GET`

**Auth required**: No

**Permissions required**: None

##### Request Syntax

N/A

##### Request Structure

N/A

##### Return type

dict

##### Returns

###### Response Syntax

```json
{
  "message": "string",
  "request": null,
  "response": {
    "string": { "string": { "clean": bool, "ttl": 123, "id": "string" } }
  }
}
```

###### Response Structure

- _(dict)_

  - **message** (string) -- If the operational was successful, the value will denote the action taken. Otherwise, the value will contain an error message.

  - **request** (dict) -- Request payload.

  - **response** (dict) -- Response payload.

    - _service (dict)_

      - _resource (dict)_

        - **clean** (boo) -- Indicator if the AWS service resource will be cleaned

        - **ttl** (123) -- Default time-to-live for the AWS service resource

        - **id** (string) -- Type of resource ID required for whitelisting
