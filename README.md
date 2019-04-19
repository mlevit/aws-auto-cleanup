# AWS Auto Cleanup

Open source application to programatically clean your AWS resources based on a whitelist and time to live (TTL) settings.

## Table of Contents

- [Setup](#setup)
  - [Deployment](#deployment)
  - [Removal](#removal)
  - [Configuration](#configuration)
- [Tables](#tables)
- [Resource Tree](#resource-tree)

## Setup
### Deployment

To deploy this Auto Cleanup to your AWS account, follow the below steps:

1. Install Serverless `npm install serverless -g`
2. Install AWS CLI `pip3 install awscli --upgrade --user`
3. Clone this repository `git clone https://github.com/servian/aws-auto-cleanup`
4. Configure AWS CLI following the instruction at [Quickly Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration). Ensure the user you're configuring has the appropriate IAM permissions to create Lambda Functions, S3 Buckets, IAM Roles, and CloudFormation Stacks. It is best for administrators to deploy Auto Cleanup.
5. If you've configure the AWS CLI using a profile, open the `serverless.yml` file and modify the `provider > profile` attribute to match your profile name.
6. Change the custom `company` attribute within the `serverless.yml` file to your company name in order to prevent S3 Bucket name collision
7. Change into the Auto Cleanup directory `cd aws-auto-cleanup`
8. Deploy Auto Cleanup `serverless deploy`
9. Invoke Auto Cleanup for the first time `serverless invoke -f AutoCleanup`
10. Check Auto Cleanup logs `serverless logs -f AutoCleanup`

### Removal

Auto Cleanup is deployed using the Serverless Framework which under the hood creates an AWS CloudFormation Stack. This means removal is clean and simple.

To remove Auto Cleanup from your AWS account, follow the below steps:

1. Change into the Auto Cleanup directory `cd aws-auto-cleanup`
2. Remove Auto Cleanup `serverless remove`

### Configuration

#### Default Values

When Auto Cleanup runs, it will populate `auto-cleanup-settings` or `auto-cleanup-whitelist` DynamoDB tables from then data files `/data/auto-cleanup-settings.json` and `/data/auto-cleanup-whitelist.json`.

#### Region

Within the `serverless.yml` file, under `provider` there is a `region` attribute. Set this attribute to your desired region.


#### Logging

Within the `serverless.yml` file, under `functions > AutoCleanup > environment` there is a `LOGLEVEL` attribute. By default, the log level is set to `INFO`. This can be changed to `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`, `CRITICAL` based on your logging requirements.

Auto Cleanup will output all resource remove logs at the `INFO` level and logs of why resources were **not** removed at the `DEBUG` level.

#### Scheduling

Within the `serverless.yml` file, under `functions > AutoCleanup > events > schedule` there is a `RATE`  and `enabled` attributes.

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

```json
{
  "key": "version",
  "value": x.x
}
```

#### General

```json
{
  "key": "general",
  "value": {
    "dry_run": true
  }
}
```

#### Services

Table includes the `clean` attribute which informs Auto Cleanup if the service should be cleaned up or not and the `ttl` attribute which stores the time to live number of days for that service resource type pair.

```json
{
  "key": "services",
  "value": {
    "cloudformation": {
      "stacks": {
        "clean": true,
        "ttl": 7
      }
    },
    "dynamodb": {
      "tables": {
        "clean": true,
        "ttl": 7
      }
    },
    "ec2": {
      "addresses": {
        "clean": true
      },
      "instances": {
        "clean": true,
        "ttl": 7
      },
      "snapshots": {
        "clean": true,
        "ttl": 7
      },
      "volumes": {
        "clean": true,
        "ttl": 7
      }
    },
    "lambda": {
      "functions": {
        "clean": true,
        "ttl": 7
      }
    },
    "rds": {
      "instances": {
        "clean": true,
        "ttl": 7
      },
      "snapshots": {
        "clean": true,
        "ttl": 7
      }
    },
    "redshift": {
      "clusters": {
        "clean": true,
        "ttl": 7
      },
      "snapshots": {
        "clean": true,
        "ttl": 7
      }
    },
    "s3": {
      "buckets": {
        "clean": true,
        "ttl": 7
      }
    }
  }
}
```

#### Region

Table includes the `clean` attribute which informs Auto Cleanup if the region should be cleaned up or not.

```json
{
  "key": "regions",
  "value": {
    "ap-northeast-1": {
      "clean": true
    },
    "ap-northeast-2": {
      "clean": true
    },
    "ap-northeast-3": {
      "clean": false
    },
    "ap-south-1": {
      "clean": true
    },
    "ap-southeast-1": {
      "clean": true
    },
    "ap-southeast-2": {
      "clean": true
    },
    "ca-central-1": {
      "clean": true
    },
    "cn-north-1": {
      "clean": false
    },
    "cn-northwest-1": {
      "clean": false
    },
    "eu-central-1": {
      "clean": true
    },
    "eu-north-1": {
      "clean": true
    },
    "eu-west-1": {
      "clean": true
    },
    "eu-west-2": {
      "clean": true
    },
    "eu-west-3": {
      "clean": true
    },
    "sa-east-1": {
      "clean": true
    },
    "us-east-1": {
      "clean": true
    },
    "us-east-2": {
      "clean": true
    },
    "us-west-1": {
      "clean": true
    },
    "us-west-2": {
      "clean": true
    }
  }
}
```

*Note: Some regions have `clean` set to `false` by default as they required special access from AWS*

#### Dry Run

The `dry_run` setting is used to inform Auto Cleanup if it should be removing resources it finds to have overstayed their welcome. By default, `dry_run` is set to `true`. This means that no resource removal will occur, however Auto Cleanup will output relevant logs as if it had removed resources. This allows you inspect the resources Auto Cleanup will be removing as well as giving you ample opportunity to add those that shouldn't be removed to the Whitelist table.

#### Time to Live (TTL)

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

| Resource              | ID Attribute           | Example Value                                  |
| --------------------- | ---------------------- | ---------------------------------------------- |
| CloudFormation Stacks | Stack Name             | `cloudformation:stack:my_cloudformation_stack` |
| DynamoDB Tables       | Table Name             | `dynamodb:table:my_dynamodb_table`             |
| EC2 Instances         | Instance ID            | `ec2:instance:i-0326701a029dbf9d0`             |
| EC2 Volumes           | Volume ID              | `ec2:volume:vol-0e1a431b9503a43aa`             |
| EC2 Snapshots         | Snapshot ID            | `ec2:snapshot:snap-00c8c90db9fdceb3c`          |
| EC2 Elastic IPs       | Allocation ID          | `ec2:address:eipalloc-03e6c42893296972f`       |
| Lambda Functions      | Function Name          | `lambda:function:my_lambda_function`           |
| Redshift Instances    | Snapshot Identifier    | `redshift:instance:my_cluster`                 |
| Redshift Snapshots    | DB Snapshot Name       | `redshift:snapshot:my_cluster_snapshot`        |
| RDS Instances         | DB Instance Identifier | `rds:snapshot:my_rds_instance`                 |
| RDS Snapshots         | DB Snapshot Name       | `rds:snapshot:my_rds_instance_snapshot`        |

## Resource Tree

An ASCI resource tree (example below) is generated with each invocation of the application. The tree is exported into the `ResourceTreeBuckett` objects within the `serverless.yml` file.

This tree allows users to visualise their AWS resources in a simple fixed width text editor.

```
AWS
├── ap-southeast-2
│   ├── CloudFormation
│   │   └── Stacks
│   │       ├── auto-cleanup-dev
│   │       └── auto-cleanup-production
│   ├── DynamoDB
│   │   └── Tables
│   │       ├── auto-cleanup-settings-dev
│   │       ├── auto-cleanup-settings-production
│   │       ├── auto-cleanup-whitelist-dev
│   │       └── auto-cleanup-whitelist-production
│   ├── EC2
│   │   ├── Addresses
│   │   │   ├── eipalloc-03e6c42893296972f
│   │   │   └── eipalloc-05065c5fa7c5b481d
│   │   ├── Instances
│   │   │   ├── i-060698bee8d6f3422
│   │   │   ├── i-07440be98bfa9a15a
│   │   ├── Snapshots
│   │   │   ├── snap-00c8c90db9fdceb3c
│   │   │   ├── snap-036ea48b4b3105598
│   │   └── Volumes
│   │       ├── vol-0652568b9c72f0bb9
│   │       ├── vol-07e62ab726cb2c520
│   ├── Lambda
│   │   └── Functions
│   │       ├── auto-cleanup-dev
│   │       └── auto-cleanup-production
│   └── Redshift
│       └── Snapshots
│           ├── redshift-cluster-1-data-loaded-1
│           └── redshift-cluster-1-snapshot-1
├── global
│   └── S3
│       └── Buckets
│           ├── auto-cleanup-dev-resourcetreebucket
│           ├── auto-cleanup-dev-serverlessdeploymentbucket-1g2bp8sh8iqqa
└── us-east-1
    ├── CloudFormation
    │   └── Stacks
    │       └── cc-iam-stack
    └── EC2
        ├── Addresses
        │   └── eipalloc-0b7a547aba879ec06
        ├── Instances
        │   └── i-0cbfb68a0d6e42c99
        └── Volumes
            └── vol-0921cdc9b3e6fc85a
```