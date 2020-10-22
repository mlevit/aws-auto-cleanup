# Coverage

| Service           | Resource Type      | Development Status | Testing Status                                                        |
| ----------------- | ------------------ | ------------------ | --------------------------------------------------------------------- |
| CloudFormation    | Stacks             | Done               | Done                                                                  |
| DynamoDB          | Tables             | Done               | Done                                                                  |
| EC2               | Addresses          | Done               | No Moto support ([issue](https://github.com/spulec/moto/issues/2221)) |
| EC2               | Instances          | Done               | Done                                                                  |
| EC2               | Security Groups    | Done               | Done                                                                  |
| EC2               | Snapshots          | Done               | Done                                                                  |
| EC2               | Volumes            | Done               | Done                                                                  |
| Elastic Beanstalk | Applications       | Done               | No Moto support                                                       |
| EMR               | Clusters           | Done               | Done                                                                  |
| Glue              | Dev Endpoints      | Done               |                                                                       |
| Kinesis           | Streams            | Done               |                                                                       |
| IAM               | Roles              | Done               | No Moto support                                                       |
| Lambda            | Functions          | Done               |                                                                       |
| RDS               | Instances          | Done               | No Moto support ([issue](https://github.com/spulec/moto/issues/2220)) |
| RDS               | Snapshots          | Done               | Done                                                                  |
| Redshift          | Clusters           | Done               | Done                                                                  |
| Redshift          | Snapshots          | Done               | Done                                                                  |
| S3                | Buckets            | Done               | Done                                                                  |
| SageMaker         | Endpoints          | Done               |                                                                       |
| SageMaker         | Notebook Instances | Done               |                                                                       |

## Todo

| Service                    | Resource Type        |
| -------------------------- | -------------------- |
| Database Migration Service | Replication Instance |
| Database Migration Service | Replication Task     |
| ECS                        | Clusters             |
| EKS                        | Clusters             |
| Elasticsearch Service      | Domain               |
| Glue                       | Crawlers             |
