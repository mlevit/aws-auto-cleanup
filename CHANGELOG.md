# AWS Auto Cleanup Changelog

## 1.1.0

- Changed CloudFormation Stacks deletion to be done in parallel to save time.
- Fixed issue where automated snapshots (Redshift and RDS) were attempted to be deleted, not just the manual ones.
- Improved S3 Bucket deletion by introducing Boto3 `resource` instead of `client`.

## 1.0.0

- Added serverless API for whitelist, exeuction logs, and settings.
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
