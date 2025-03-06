# Check Status Lambda Function Module

This module provisions a Lambda function that checks the status of Entity Resolution jobs.

## Features

- Automatic status checking of Entity Resolution jobs
- VPC support for enhanced security
- Configurable memory and timeout settings
- CloudWatch logging integration
- Custom IAM role with least privilege access

## Usage

```hcl
module "check_status_lambda" {
  source = "./modules/lambda-functions/check-status"

  project_name          = "entity-resolution"
  aws_region           = "us-west-2"
  s3_bucket_name       = "my-entity-resolution-bucket"
  s3_input_prefix      = "input/"
  s3_output_prefix     = "output/"
  er_workflow_name     = "my-workflow"
  er_schema_name       = "my-schema"
  er_entity_attributes = ["name", "address", "phone"]

  subnet_ids           = ["subnet-123", "subnet-456"]
  vpc_id              = "vpc-789"

  default_tags = {
    Environment = "production"
    Project     = "entity-resolution"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 4.0 |

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| project_name | Name of the project | string | yes |
| aws_region | AWS region | string | yes |
| s3_bucket_name | S3 bucket for data storage | string | yes |
| s3_input_prefix | S3 prefix for input data | string | yes |
| s3_output_prefix | S3 prefix for output data | string | yes |
| er_workflow_name | Entity Resolution workflow name | string | yes |
| er_schema_name | Entity Resolution schema name | string | yes |
| er_entity_attributes | List of entity attributes | list(string) | yes |
| subnet_ids | List of subnet IDs for VPC deployment | list(string) | no |
| vpc_id | VPC ID for deployment | string | no |
| default_tags | Default tags for resources | map(string) | yes |

## Outputs

| Name | Description |
|------|-------------|
| lambda_function_arn | ARN of the created Lambda function |
| lambda_function_name | Name of the created Lambda function |
| lambda_role_arn | ARN of the Lambda execution role |

## Security Considerations

- Function runs within a VPC when subnet_ids are provided
- IAM roles follow least privilege principle
- CloudWatch logs are encrypted
- S3 access is restricted to specific bucket and prefixes
