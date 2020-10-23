# AWS Auto Cleanup Changelog

## 1.1.0

- Added default sorting (key in descending order) on execution log list table.
- Changed CloudFormation Stacks deletion to be processed in parallel.
- Fixed issue where automated snapshots (Redshift and RDS) were attempted to be deleted, not just the manual ones.
- Improved S3 Bucket deletion by introducing Boto3 `resource` instead of `client`.
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
