# Contributing

Thank you for your interest in contributing to AWS Auto Cleanup. To start contributing first fork our repository into your own Github account, and create a local clone of it. The latter will be used to get new features implemented or bugs fixed. Once done and you have the code locally on the disk, you can get started. We advice to not work directly on the master branch, but to create a separate branch for each issue you are working on. That way you can easily switch between different work, and you can update each one for latest changes on upstream master individually.

## Writing Code

### Developing

Before developing your cleanup function, please refer to our [COVERAGE.md](COVERAGE.md) page which includes all cleanup functions and their development/testing status'.

Please ensure you create a **single** cleanup function with the same name as the resource with the service class.

Each function should contain a [Python docstring](https://www.python.org/dev/peps/pep-0257/) matching the formatting found inside the repository.

Example:

```python
def s3_bucket_ssl_requests_only(self, resource_id):
    """Adds Bucket Policy to force SSL only connections

    Arguments:
    resource_id {string} -- S3 Bucket name

    Returns:
    boolean -- True if remediation was successful
    """
```

### Testing

AWS Auto Cleanup utilises the [Moto Python library](https://github.com/spulec/moto/) for automated testing via [pytest](https://docs.pytest.org/en/latest/). For each new function written to cleanup a resource, please ensure a new test class is created within the `test` folder. This class should incorporate functions for both positive and negative tests. See [Moto's Implementation Coverage](https://github.com/spulec/moto/blob/master/IMPLEMENTATION_COVERAGE.md) page for all supported mock API calls.

If the API calls within your new cleanup function are not covered by Moto, please ensure the [COVERAGE.md](COVERAGE.md) is updated with `No Moto support` for your particular cleanup.

### Formatting

AWS Auto Cleanup is using the [Python Black](https://github.com/python/black) code formatter for Python and [Prettier](https://prettier.io/) code formatter for all YAML and JSON formatting. Please ensure your code is correctly formatted before submitting a pull request. If you're unclear about how to correctly format your code just look at existing code base for inspiration.

## Submitting Changes

When you think your code is ready for review create a pull request within GitHub. Maintainers of the repository will watch out for new PR‘s and review them in regular intervals.

By default, for each change in the PR will automatically trigger pytests, Serverless AWS deployment via [Travis CI](https://travis-ci.org/servian/aws-auto-cleanup) as well as a code quality review via [Codacy](https://app.codacy.com/project/servian/aws-auto-cleanup/dashboard). If either Travis CI or Codacy fails make sure to address the failures immediately.

If comments have been given in a review, they have to get integrated. For those changes a separate commit should be created and pushed to your remote development branch. Don’t forget to add a comment in the PR afterward, so everyone gets notified by GitHub. Keep in mind that reviews can span multiple cycles until the maintainers are happy with the code.
