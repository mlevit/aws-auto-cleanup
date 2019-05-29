# Coverage

Below tables represent the coverage of Auto Remediate. Automated testing of Auto Remediate is done using the [Moto](https://github.com/spulec/moto) Python library.

Development coverage: **24 of 24**

Test coverage: **10 of 24**

| Service           | Resource Type   | Development Status | Testing Status                                                        |
| ----------------- | --------------- | ------------------ | --------------------------------------------------------------------- |
| CloudFormation    | Stacks          | Done               | Done                                                                  |
| DynamoDB          | Tables          | Done               | Done                                                                  |
| EC2               | Addresses       | Done               | No Moto support ([issue](https://github.com/spulec/moto/issues/2221)) |
|                   | Instances       | Done               | Done                                                                  |
|                   | Security Groups | Done               | Done                                                                  |
|                   | Snapshots       | Done               | Done                                                                  |
|                   | Volumes         | Done               | Done                                                                  |
| Elastic Beanstalk | Applications    | Done               | No Moto support                                                       |
| EMR               | Clusters        | Done               | Done                                                                  |
| IAM               | Roles           | Done               | No Moto support                                                       |
| Lambda            | Functions       | Done               |                                                                       |
| RDS               | Instances       | Done               | No Moto support ([issue](https://github.com/spulec/moto/issues/2220)) |
|                   | Snapshots       | Done               | Done                                                                  |
| Redshift          | Clusters        | Done               | Done                                                                  |
|                   | Snapshots       | Done               | Done                                                                  |
| S3                | Buckets         | Done               | Done                                                                  |
