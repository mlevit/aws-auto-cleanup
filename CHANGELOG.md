# Changelog

## UNRELEASED

- Added KMS Key cleanup.

## 2.4.0

- Updated Allowlist display hiding Owner and Comment columns behind a expand button. This will allow for a more clean display of resources and their ID's.
- Changed the date used to calculate the age of an EC2 Instance. Instead of using the EC2 Instance `LaunchTime` which resets everytime an EC2 Instance is stopped and started, the EC2 Instance's ENI `AttachTime` is used instead. [#129](https://github.com/servian/aws-auto-cleanup/issues/129).
- Updated homescreen design with an encapsulated allowlist and execution log, including a number of QoL changes.

## 2.3.0

- Added support for very large (20K+) execution log files.
- Added better resource ID placeholders giving users a better indication of expected value.
- Deprecated option to allowlist resources from execution log.
- Fixed issue with not being able to allowlist ECR Images.

## 2.2.0

- Added wildcard support to allowlist resource ID. Comparisons are now performed using the [fnmatch](https://docs.python.org/3/library/fnmatch.html) Python module. The following special characters can be used:

  | Pattern | Meaning                          |
  | ------- | -------------------------------- |
  | \*      | matches everything               |
  | ?       | matches any single character     |
  | [seq]   | matches any character in seq     |
  | [!seq]  | matches any character not in seq |

- Added Kafka Serverless Cluster cleanup.
- Fixed mismatch between app settings and exeuction log for Elastic Beanstalk and Elasticsearch Service. This prevented allowlisting via the execution log in the web app.

## 2.1.0

- Added RDS Cluster and Cluster Snapshot cleanup.
- Migrated to Python 3.9.

## 2.0.0

- Added Transfer Family Server (SFTP, FTPS, and FTP) cleanup.
- Replaced all references to `whitelist` with `allowlist`.

## 1.6.0

- Added NAT Gateway cleanup.
- Added support for Serverless V3.

## 1.5.5

- Fixed issue that was introduced in 1.5.4. Deleted Cloudformation Stack Resources no longer have a `PhysicalResourceId` property. This caused an error when attempting to allowlist the Stack Resources.

## 1.5.4

- Fixed issue with CloudFormation Stack allowlisted Managed Policies. Whilst the Managed Policies were allowlisted, their resource was `ManagedPolicy` and not `Policy` which is checked for allowlisting.

## 1.5.3

- Added missing execution log action for allowlisted EC2 Security Groups.
- Reduced EC2 Security Group cleanup complexity.
- Resolved Serverless deprecation warnings.

## 1.5.2

- Converted execution log timestamp to local time.

## 1.5.1

- Fixed broken EC2 Instance cleanup. The existing filter on the `describe-instances` API request was invalid and filtering out all EC2 instances.
- Modified the TTL expiration set when adding new allowlist entries. New entries will now be allowlisted for double the TTL duration. In other words, when creating a new EC2 instance, it will automatically be allowlisted for 14 days instead of the default 7. The previous functionality didn't make too much sense as the allowlisting duration was the same as the default non-allowlisted behaviour.

## 1.5.0

- Added API authentication (thanks to @miki79)
- Added API key prompt to the web app (thanks to @miki79).
- Added CloudFormation nested Stack allowlisted when the parent or root Stacks are allowlisted.
- Fixed `execution_log` Glue table.

## 1.4.0

- Added ability to allowlist entries directly from the execution log.
- Added IAM Access Key and User cleanup.
- Added Managed Workflows for Apache Airflow cleanup.
- Added paginated resource retrieval where possible.
- Added parallel cleanup of S3 Buckets.
- Added SageMaker App cleanup.
- Removed CloudFormation Stack deletion waiting as it was raising API throttling errors.

## 1.3.0

- Added CloudWatch Log Group cleanup.
- Added ECR Image and Repository cleanup.
- Added EKS Cluster, Fargate Profile, and Node Group cleanup.
- Added Glue Crawler cleanup.
- Added Glue Database cleanup.
- Added IAM Policy cleanup.
- Added paginated Allowlist retrieval.
- Added parallel cleanup of global services (e.g., S3, IAM).
- Fixed broken pagination for IAM, Glue, and CloudWatch.
- Fixed Redshift Cluster deletion. Redshift Clusters were not deleted unless their status was `available`.
- Removed API caching.

## 1.2.0

- Added Amplify Apps cleanup.
- Added EFS File System cleanup.
- Added ElastiCache Cluster and Replication Group cleanup.
- Added ELB Load Balancer cleanup.
- Added Kafka Cluster cleanup.
- Added paginated IAM Role retrieval.
- Added `permanent` field to the Create Allowlist API allowing the creation of permanent allowlist entries. This is however not exposed via the web UI.
- Added point-in-time recovery to the Allowlist and Settings DynamoDB tables.
- Added Allowlist table groupings to separate the permanent and temporary entries. As a side note, any entry with an expiration epoch of `4102444800` (2100-01-01 00:00:00) or greater will be considered "permanent".
- Fixed an issue where AWS managed roles, roles beginning with `AWSServiceRoleFor` were being incorrectly marked as `SKIP - WHITELIST`. These roles are now ignored during cleanup.
- Improved accuracy of actions taken within execution logs.

## 1.1.0

- Added AWS Account ID to the navigation bar and webpage title.
- Added default sorting (by log name in descending order) within the execution log list table. This ensures the latest execution logs are always first.
- Added EC2 Image (AMI) cleanup.
- Added execution log statistics to the execution log popup. Statistics include a breakdown of counts by service, action taken, and region.
- Added help section to the website introducing new users to Auto Cleanup as well as exposing AWS service settings from the Settings table.
- Fixed an issue where Auto Cleanup was attempting to delete automated Redshift and RDS snapshots. Only manual snapshots can be deleted.
- Fixed an issue where EC2 Snapshots were incorrectly marked as "in use" and not deleted.
- Improved CloudFormation Stacks deletion. Stack deletions are now processed in parallel for a given region.
- Improved execution logging with finer-grained information.
- Improved S3 Bucket deletion by using Boto3 `resource` instead of `client`.
- Modified AWS Auto Cleanup App memory allocation from 256 MB to 512 MB.
- Modified AWS Auto Cleanup App timeout from 5 minutes to 15 minutes.

## 1.0.0

- Added serverless API for allowlist, execution logs, and settings.
- Added support for missing regions:
  - af-south-1
  - ap-east-1
  - eu-south-1
  - me-south-1
- Added support for new services:
  - ECS Clusters and Services
  - Elasticsearch Service Domains
  - Kinesis Streams
  - SageMaker Endpoints and Notebook Instances
- Added web UI for managing your allowlist and viewing execution logs.
- Replaced GPLv3 with MIT license.
