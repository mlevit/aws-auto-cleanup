# AWS Auto Cleanup Changelog

## 1.1.0

- Added default sorting (by Key in descending order) within the execution log list table. This ensures the latest execution logs are always first.
- Added execution log statistics to the execution log popup. Statistics include a breakdown of counts by service, action taken, and region.
- Added help section to the website introducing new users to Auto Cleanup as well as exposing AWS service settings from the Settings table.
- Fixed an issue where Auto Cleanup was attempting to delete automated Redshift and RDS snapshots. Only manual snapshots can be deleted.
- Improved CloudFormation Stacks deletion. Stack Deletions are now be processed in parallel.
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
