# AWS Auto Cleanup

Open source application to programatically clean your AWS resources based on a whitelist and time to live (TTL) settings.

## Deployment

To deploy this Auto Cleanup to your AWS account, follow the below steps:

1. Install Serverless `npm install serverless -g`

2. Install AWS CLI `pip3 install awscli --upgrade --user`

3. Clone this repository `git clone https://github.com/servian/aws-auto-cleanup`

4. Configure AWS CLI following the instruction at [Quickly Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration). Ensure the user you're configuring has the appropriate IAM permissions to create Lambda Functions, S3 Buckets, IAM Roles, and CloudFormation Stacks. It is best for administrators to deploy Auto Cleanup.

5. If you've configure the AWS CLI using a profile, open the `serverless.yml` file and modify the `provider > profile` attribute to match your profile name.

6. Change into the Auto Cleanup directory `cd aws-auto-cleanup`

7. Deploy Auto Cleanup `serverless deploy`

8. Invoke Auto Cleanup for the first time `serverless invoke -f AutoCleanup`

9. Check Auto Cleanup logs `serverless logs -f AutoCleanup`

### Removing

Auto Cleanup is deployed using the Serverless Framework which under the hood creates an AWS CloudFormation Stack. This means removal is clean and simple.

To remove Auto Cleanup from your AWS account, follow the below steps:

1. Change into the Auto Cleanup directory `cd aws-auto-cleanup`
2. Remove Auto Cleanup `serverless remove`

### Default Values

When Auto Cleanup runs, it will populate `auto-cleanup-settings` or `auto-cleanup-whitelist` DynamoDB tables from then data files `/data/auto-cleanup-settings.json` and `/data/auto-cleanup-whitelist.json`.

### Region

Within the `serverless.yml` file, under `provider` there is a `region` attribute. Set this attribute to your desired region.


### Logging

Within the `serverless.yml` file, under `functions > AutoCleanup > environment` there is a `LOGLEVEL` attribute. By default, the log level is set to `INFO`. This can be changed to `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`, `CRITICAL` based on your logging requirements.

Auto Cleanup will output all resource remove logs at the `INFO` level and logs of why resources were **not** removed at the `DEBUG` level.

### Scheduling

Within the `serverless.yml` file, under `functions > AutoCleanup > events > schedule` there is a `RATE`  and `enabled` attributes.

You can enable custom scheduling of the Lambda by following the instruction at [Schedule Expressions Using Rate or Cron](https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html).

The `enabled` attribute allows you to quickly enable or disable the scheduling functionality.

## Tables

Auto Cleanup uses two Amazon DynamoDB tables `auto-cleanup-settings` and `auto-cleanup-whitelist`.

### Settings

The Settings table contains all key-value pair settings used by Auto Cleanup during runtime.

The **resource** category holds all the time to live settings for each service and resource pair. By default they are all set to 7 days.

The **region** category allows users to turn region scanning on and off to either expand their search or reduce the run-time of Auto Cleanup.

By default, the below settings are automatically inserted the first time Auto Cleanup is run:

| key                           | category | value |
| ----------------------------- | -------- | ----- |
| dry_run                       | general  | true  |
| cloudformation_stack_ttl_days | resource | 7     |
| dynamodb_table_ttl_days       | resource | 7     |
| ec2_instance_ttl_days         | resource | 7     |
| ec2_snapshot_ttl_days         | resource | 7     |
| ec2_volume_ttl_days           | resource | 7     |
| lambda_function_ttl_days      | resource | 7     |
| rds_instance_ttl_days         | resource | 7     |
| rds_snapshot_ttl_days         | resource | 7     |
| s3_bucket_ttl_days            | resource | 7     |
|us-east-2|region|true|
|us-east-1|region|true|
|us-west-1|region|true|
|us-west-2|region|true|
|ap-south-1|region|true|
|ap-northeast-3 *|region|false|
|ap-northeast-2|region|true|
|ap-southeast-1|region|true|
|ap-southeast-2|region|true|
|ap-northeast-1|region|true|
|ca-central-1|region|true|
|cn-north-1 \*|region|false|
|cn-northwest-1 \*|region|false|
|eu-central-1|region|true|
|eu-west-1|region|true|
|eu-west-2|region|true|
|eu-west-3|region|true|
|eu-north-1|region|true|
|sa-east-1|region|true|
|us-gov-east-1|region|true|
|us-gov-west-1|region|true|

\* Regions only available to select customers

#### Dry Run

The `dry_run` setting is used to inform Auto Cleanup if it should be removing resources it finds to have overstayed their welcome. By default, `dry_run` is set to `true`. This means that no resource removal will occur, however Auto Cleanup will output relevant logs as if it had removed resources. This allows you inspect the resources Auto Cleanup will be removing as well as giving you ample opportunity to add those that shouldn't be removed to the Whitelist table.

#### Time to Live

In order to understand which resources have overstayed their welcome, Auto Cleanup will look at the resources created date time or last modified date time (which ever exists) and compare that to the time to live setting for that particular service resource type. If the resources was created or last modified longer than the number of days for that resources time to live setting, it will be removed.

At any time, you may modify the time to live settings for any service resource type within the `auto-cleanup-settings` Amazon DynamoDB table.

### Whitelist

The Whitelist table allows users to add their resources to prevent removal.

The Whitelist table as the following schema and comes pre-populated with Auto Cleanup resources to ensure Auto Cleanup does not remove itself:

| Column      | Format                                      | Description                                                  |
| ----------- | ------------------------------------------- | ------------------------------------------------------------ |
| resource_id | `<service>:<resource type>:<resource name>` | Unique identifier of the resource. This is a custom format base on the service (e.g., EC2, S3), the resource type (e.g., Instance, Bucket) and resource name. |
| expire_at   | EPOCH timestamp                             | EPOCH timestamp no later than 7 days from insert date        |
| comment     | Text field                                  | Comment field describing the resource and why it has been whitelisted |
| owner_email | Email address                               | Email address of the resource owner in case they need to be contacted regarding the whitelisting |

Adding resources to the Whitelist table will ensure those resources are not removed by Auto Cleanup.

The below table lists the resource attribute that should be used for unique identification of resources for whitelisting.

| Resource              | ID Attribute     | Example Value                                 |
| --------------------- | ---------------- | --------------------------------------------- |
| CloudFormation Stacks | Stack Name       | `cloudformation:stack:auto-cleanup-dev`       |
| DynamoDB Tables       | Table Name       | `dynamodb:table:auto-cleanup-logs-dev`        |
| EC2 Instances         | Instance ID      | `ec2:instance:i-0326701a029dbf9d0`            |
| EC2 Volumes           | Volume ID        | `ec2:volume:vol-0e1a431b9503a43aa`            |
| EC2 Snapshots         | Snapshot ID      | `ec2:snapshot:snap-00c8c90db9fdceb3c`         |
| EC2 Elastic IPs       | Allocation ID    | `ec2:address:eipalloc-03e6c42893296972f`      |
| Lambda Functions      | Function Name    | `lambda:function:auto-cleanup-prd`            |
| RDS Instances         | DB Identifier    | `rds:instance:auto-cleanup-db`                |
| RDS Snapshots         | DB Snapshot Name | `rds:snapshot:rds:auto-cleanup-db-2019-01-01` |

## Todo

- [x] Serverless.com packaging and deployment
- [ ] CloudFormation
  - [x] IAM Role for Lambda
  - [ ] S3 Bucket
  - [x] DynamoDB tables `auto-cleanup-settings` and `auto-cleanup-whitelist`
  - [x] DynamoDB default values for settings and whitelist table
- [ ] Static site (React.js and Lambda) to expose DynamoDB tables for users to add to and remove from and extend the life of their whitelisting