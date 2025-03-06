# Changes to make prior to 1.0.0

## Python

* Remove Snowflake source account since snowflake is only used during loading snowflake.
* Suggest alternative package names more obvious to the architecture pattern being followed
* Improve pre-commit for 1.0.0
* Improve/implement editorconfig and other tools to maintain a consistent codebase
* Review plan to adopt similar pattern across all services
* Fix ruff linting
* Fix mypy static type analysis
* Fix all unit tests
* Determine if Python schema validation is duplicate of Terraform's config validation
* Icrease Unit test structure
* Improve use of moto
* Update documentation and architecture
* Replace use of SSM with environment variables
* DOes pydantic really help with such a small amount of config?

## Terraform

* Add support for Entity Resolution input/output to use precreated S3 Bucket & KMS Key
* Make an optional Lambda to trigger Step Functions and act as target for event driven architectures
* Enhance terraform return values to allow the architecture to be extendable, such as returning important ARNs
* Standardize documentation
* Improve pre-commit for 1.0.0
* Fix all linting issues
* Add unit tests
* Update documentation and architecture
