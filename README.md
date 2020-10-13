![](./static/banner.png)

<p align="center">
<a href="https://travis-ci.org/servian/aws-auto-cleanup"><img src="https://travis-ci.org/servian/aws-auto-cleanup.svg?branch=master"></a> <a href="https://www.codacy.com/app/servian/aws-auto-cleanup?utm_source=github.com&utm_medium=referral&utm_content=servian/aws-auto-cleanup&utm_campaign=Badge_Grade"><img src="https://api.codacy.com/project/badge/Grade/4f20fbbb03464b9aa6c558a4415d2288"></a> <a href="https://www.codacy.com/app/servian/aws-auto-cleanup?utm_source=github.com&utm_medium=referral&utm_content=servian/aws-auto-cleanup&utm_campaign=Badge_Coverage"><img src="https://api.codacy.com/project/badge/Coverage/4f20fbbb03464b9aa6c558a4415d2288"></a>
</p>

<p align="center">
Open-source application to programmatically delete AWS resources based on a whitelist and time to live (TTL) settings.
</p>
<br/>
<p align="center">
Auto Cleanup is comprised of two applications, core and web. Click through to learn more and follow the steps to deploy the applications to your environment.
</p>

|                                                 [![app](./static/app.png)](./app/)                                                  |                                                      [![web](./static/web.png)](./web/)                                                       |
| :---------------------------------------------------------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------: |
| The core application is a serverless stack running within a Lambda environment with supporting DynamoDB tables, S3 buckets and more | The web application is a supported serverless stack that enables users to more easily whitelist AWS resources, view executions logs, and more |
