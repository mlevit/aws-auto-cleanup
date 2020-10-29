# AWS Auto Cleanup Changelog

## 1.2.0

- Added Boto3 pagination to IAM Role retrieval.
- Added point-in-time recovery to the Whitelist and Settings DynamoDB tables.
- Added Whitelist table groupings to separate the permanent and temporary entries. As a side note, any entry with an expiration epoch of `4102444800` or greater will be considered "permanent".
- Fixed an issue where AWS managed roles, roles beginning with `AWSServiceRoleFor` were being incorrectly marked as `skip - whitelist`. These roles are now ignored during cleanup.

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

- Added serverless API for whitelist, execution logs, and settings.
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
- Added web UI for managing your whitelist and viewing execution logs.
- Replaced GPLv3 with MIT license.
