# AWS Auto Cleanup

[![Build Status](https://travis-ci.org/servian/aws-auto-cleanup.svg?branch=master)](https://travis-ci.org/servian/aws-auto-cleanup) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/4f20fbbb03464b9aa6c558a4415d2288)](https://www.codacy.com/app/servian/aws-auto-cleanup?utm_source=github.com&utm_medium=referral&utm_content=servian/aws-auto-cleanup&utm_campaign=Badge_Grade) [![Codacy Badge](https://api.codacy.com/project/badge/Coverage/4f20fbbb03464b9aa6c558a4415d2288)](https://www.codacy.com/app/servian/aws-auto-cleanup?utm_source=github.com&utm_medium=referral&utm_content=servian/aws-auto-cleanup&utm_campaign=Badge_Coverage)

![Release](https://img.shields.io/github/release/servian/aws-auto-cleanup.svg) ![Release Date](https://img.shields.io/github/release-date/servian/aws-auto-cleanup.svg)

![Language](https://img.shields.io/github/languages/top/servian/aws-auto-cleanup.svg) [![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com) [![Python Black](https://img.shields.io/badge/code%20style-black-000000.svg?label=Python%20code%20style)](https://github.com/python/black) [![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?label=Markdown%2FYAML%20code%20style)](https://github.com/prettier/prettier)

Open-source application to programmatically clean your AWS resources based on a whitelist and time to live (TTL) settings.

## Table of Contents

- [Setup](#setup)
  - [Deployment](#deployment)
  - [Removal](#removal)
  - [Configuration](#configuration)
- [Tables](#tables)
- [Actions Taken](#actions-taken)
- [Web Application](#web-application)
- [Contributing](CONTRIBUTING.md)

## Setup

### Deployment

1.  Install the [Serverless Framework](https://serverless.com/)

```bash
npm install serverless --global
```

2.  Install [AWS CLI](https://aws.amazon.com/cli/)

```bash
pip3 install awscli --upgrade --user
```

3.  Configure the AWS CLI following the instruction at [Quickly Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration). Ensure the user you're configuring has the appropriate IAM permissions to create Lambda Functions, S3 Buckets, IAM Roles, and CloudFormation Stacks. It is best for administrators to deploy Auto Cleanup.

4.  Install Auto Cleanup

```bash
serverless create --template-url https://github.com/servian/aws-auto-cleanup --path aws-auto-cleanup
```

5.  Change into the Auto Cleanup directory

```bash
cd aws-auto-cleanup
```

8.  Install Serverless plugins needed for deployment

```bash
serverless plugin install --name serverless-python-requirements
npm install serverless-iam-roles-per-function
npm install serverless-s3-remover
```

9.  Deploy Auto Cleanup to your AWS account

```bash
serverless deploy [--region <AWS region>] [--aws-profile <AWS CLI profile>]
```

10. Invoke Auto Cleanup for the first time to create the necessary AWS Config rules and settings

```bash
serverless invoke --function AutoCleanup [--region <AWS region>] [--aws-profile <AWS CLI profile>] --type Event
```

11. Check Auto Cleanup logs

```bash
serverless logs --function AutoCleanup [--region <AWS region>] [--aws-profile <AWS CLI profile>]
```

### Removal

Auto Cleanup is deployed using the Serverless Framework which under the hood creates an AWS CloudFormation Stack allowing for a clean and simple removal process.

To remove Auto Cleanup from your AWS account, follow the below steps:

1.  Change into the Auto Cleanup directory

```bash
cd aws-auto-cleanup
```

2.  Remove Auto Cleanup from your AWS account

```bash
serverless remove [--region <AWS region>] [--aws-profile <AWS CLI profile>]
```

### Configuration

#### Default Values

When Auto Cleanup runs, it will populate `auto-cleanup-settings` or `auto-cleanup-whitelist` DynamoDB tables from then data files `auto_cleanup/data/auto-cleanup-settings.json` and `auto_cleanup/data/auto-cleanup-whitelist.json`.

#### Logging

Within the `serverless.yml` file, under `functions > AutoCleanup > environment` there is a `LOGLEVEL` attribute. By default, the log level is set to `INFO`. This can be changed to `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`, `CRITICAL` based on your logging requirements.

Auto Cleanup will output all resource remove logs at the `INFO` level and logs of why resources were **not** removed at the `DEBUG` level.

#### Scheduling

Within the `serverless.yml` file, under `functions > AutoCleanup > events > schedule` there is a `RATE` and `enabled` attributes.

You can enable custom scheduling of the Lambda by following the instruction at [Schedule Expressions Using Rate or Cron](https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html).

The `enabled` attribute allows you to quickly enable or disable the scheduling functionality.

## Tables

Auto Cleanup uses two Amazon DynamoDB tables `auto-cleanup-settings` and `auto-cleanup-whitelist`.

### Settings

The Settings table contains all key-value pair settings used by Auto Cleanup during runtime.

The **resource** category holds all the time to live settings for each service and resource pair. By default they are all set to 7 days.

The **region** category allows users to turn region scanning on and off to either expand their search or reduce the run-time of Auto Cleanup.

By default, the below settings are automatically inserted when Auto Cleanup is run.

#### Version

The version is used to inform Auto Cleanup if new settings exist in the default data file that should be loaded into DynamoDB. If the version present in the default data file is greater than the version in DynamoDB table, the load will commence.

| Key     | Value |
| ------- | ----- |
| Version | x.x   |

#### General

| Key     | Value |
| ------- | ----- |
| Dry Run | True  |

#### Services

Table includes the `clean` attribute which informs Auto Cleanup if the service should be cleaned and the `ttl` attribute which stores the time to live in days for that service resource pair.

| Service           | Resource Type   | Clean | TTL |
| ----------------- | --------------- | ----- | --- |
| CloudFormation    | Stacks          | True  | 7   |
| DynamoDB          | Tables          | True  | 7   |
| EC2               | Addresses       | True  | N/A |
|                   | Instances       | True  | 7   |
|                   | Security Groups | True  | N/A |
|                   | Snapshots       | True  | 7   |
|                   | Volumes         | True  | 7   |
| Elastic Beanstalk | Applications    | True  | 7   |
| EMR               | Clusters        | True  | 7   |
| Glue              | Dev Endpoints   | True  | 7   |
| IAM               | Roles           | True  | 30  |
| Lambda            | Functions       | True  | 30  |
| RDS               | Instances       | True  | 7   |
|                   | Snapshots       | True  | 7   |
| Redshift          | Clusters        | True  | 7   |
|                   | Snapshots       | True  | 7   |
| S3                | Buckets         | True  | 30  |

#### Regions

Table includes the `clean` attribute which informs Auto Cleanup if the region should be cleaned up or not.

| Region            | Clean |
| ----------------- | ----- |
| ap-northeast-1    | True  |
| ap-northeast-2    | True  |
| ap-northeast-3 \* | False |
| ap-south-1        | True  |
| ap-southeast-1    | True  |
| ap-southeast-2    | True  |
| ca-central-1      | True  |
| cn-north-1 \*     | False |
| cn-northwest-1 \* | False |
| eu-central-1      | True  |
| eu-north-1        | True  |
| eu-west-1         | True  |
| eu-west-2         | True  |
| eu-west-3         | True  |
| sa-east-1         | True  |
| us-east-1         | True  |
| us-east-2         | True  |
| us-west-1         | True  |
| us-west-2         | True  |

_Note: Some regions have `clean` set to `false` by default as they required special access from AWS_

#### Dry Run

The `dry_run` setting is used to inform Auto Cleanup if it should be removing resources it finds to have overstayed their welcome. By default, `dry_run` is set to `true`. This means that no resource removal will occur, however Auto Cleanup will output relevant logs as if it had removed resources. This allows you inspect the resources Auto Cleanup will be removing as well as giving you ample opportunity to add those that shouldn't be removed to the Whitelist table.

#### Time to Live (TTL)

In order to understand which resources have overstayed their welcome, Auto Cleanup will look at the resources created date time or last modified date time (which ever exists) and compare that to the time to live setting for that particular service resource type. If the resources was created or last modified longer than the number of days for that resources time to live setting, it will be removed.

At any time, you may modify the time to live settings for any service resource type within the `auto-cleanup-settings` Amazon DynamoDB table.

### Whitelist

The Whitelist table allows users to add their resources to prevent removal.

The Whitelist table as the following schema and comes pre-populated with Auto Cleanup resources to ensure Auto Cleanup does not remove itself.

| Column      | Format                                      | Description                                                                                                                                                   |
| ----------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| resource_id | `<service>:<resource type>:<resource name>` | Unique identifier of the resource. This is a custom format base on the service (e.g., EC2, S3), the resource type (e.g., Instance, Bucket) and resource name. |
| expiration  | EPOCH timestamp                             | EPOCH timestamp no later than 7 days from insert date                                                                                                         |
| comment     | Text field                                  | Comment field describing the resource and why it has been whitelisted                                                                                         |
| owner       | Text field                                  | Email address or name of the resource owner in case they need to be contacted regarding the whitelisting                                                      |

Adding resources to the Whitelist table will ensure those resources are not removed by Auto Cleanup.

The below table lists the resource attribute that should be used for unique identification of resources for whitelisting.

| Resource                       | ID Attribute           | Example Value                                  |
| ------------------------------ | ---------------------- | ---------------------------------------------- |
| CloudFormation Stacks          | Stack Name             | `cloudformation:stack:my_cloudformation_stack` |
| DynamoDB Tables                | Table Name             | `dynamodb:table:my_dynamodb_table`             |
| EC2 Elastic IPs                | Allocation ID          | `ec2:address:eipalloc-03e6c42893296972f`       |
| EC2 Instances                  | Instance ID            | `ec2:instance:i-0326701a029dbf9d0`             |
| EC2 Security Groups            | Group ID               | `ec2:security_group:sg-09ef7b767c3ff4071`      |
| EC2 Snapshots                  | Snapshot ID            | `ec2:snapshot:snap-00c8c90db9fdceb3c`          |
| EC2 Volumes                    | Volume ID              | `ec2:volume:vol-0e1a431b9503a43aa`             |
| Elastic Beanstalk Applications | Application Name       | `elasticbeanstalk:application:my-app`          |
| EMR Clusters                   | ID                     | `emr:cluster:j-KCXVNHG2W4QK`                   |
| Glue Dev Endpoints             | Endpoint Name          | `glue:dev_endpoint:my_endpoint`                |
| IAM Roles                      | Role Name              | `iam:role:auto-cleanup-role`                   |
| Lambda Functions               | Function Name          | `lambda:function:my_lambda_function`           |
| Redshift Instances             | Cluster Identifier     | `redshift:instance:my_cluster`                 |
| Redshift Snapshots             | Snapshot Identifier    | `redshift:snapshot:my_cluster_snapshot`        |
| RDS Instances                  | DB Instance Identifier | `rds:instance:my_rds_instance`                 |
| RDS Snapshots                  | DB Snapshot Name       | `rds:snapshot:my_rds_instance_snapshot`        |
| S3 Buckets                     | Bucket Name            | `s3:bucket:auto-cleanup-bucket`                |

_Note:_ Resources that are a part of a CloudFormation Stack will be automatically whitelisted at run time to prevent the need to whitelist the CloudFormation Stack and each resource the Stack provisions.

## Actions Taken

Each action taken by Auto Cleanup is recorded and stored as a flat CSV file within the `actionstaken` S3 Bucket. Alongside the S3 Bucket, a new `auto_cleanup` Glue Database and `actions_taken` Glue Table have been created to query the data via Amazon Athena.

The `actions_taken` table has the following schema:

| Column      | Format    | Description                                                                                         |
| ----------- | --------- | --------------------------------------------------------------------------------------------------- |
| platform    | string    | Always `AWS`                                                                                        |
| region      | string    | Region (e.g. `ap-southeast-2`)                                                                      |
| service     | string    | Service (e.g., `S3`)                                                                                |
| resource    | string    | Resource (e.g., `Bucket`)                                                                           |
| resource_id | string    | Resource ID (e.g., ARN)                                                                             |
| action      | string    | Action taken on the resource (e.g., `delete`, `skip - TTL`, `skip - whitelist`, `skip`, or `error`) |
| timestamp   | timestamp | Timestamp when action was performed                                                                 |
| is_dry_run  | boolean   | Dry run activated                                                                                   |

## Web Application

### API

A simple CRUD API has been built to work alongside the web application.

**Whitelist**

- [Create Whitelist Entry](./web/docs/create_whitelist_entry.md)
- [Read Whitelist Entries](./web/docs/read_whitelist.md)
- [Update Whitelist Entry](./web/docs/update_whitelist_entry.md)
- [Delete Whitelist Entry](./web/docs/delete_whitelist_entry.md)

**Settings**

- [Read Settings Service](./web/docs/read_settings_service.md)
- [Read Settings Service](./web/docs/read_settings_resource.md)
