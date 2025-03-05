# AWS Entity Resolution Pipeline

This Terraform project deploys a serverless pipeline for AWS Entity Resolution processing, with support for long-running jobs.

## Architecture

The solution uses a combination of AWS services to handle entity resolution jobs that can take longer than the 15-minute Lambda timeout limit:

1. **AWS Step Functions** orchestrates the workflow and manages the long-running process
2. **AWS Lambda** functions handle individual steps of the pipeline
3. **AWS Entity Resolution** performs the actual matching process
4. **Amazon S3** stores input and output data
5. **Amazon CloudWatch** provides monitoring and alerting

### Process Flow

1. A scheduled EventBridge rule triggers the Step Functions workflow
2. The workflow extracts data from Snowflake and stores it in S3
3. The process Lambda initiates an Entity Resolution matching job but doesn't wait for completion
4. The Step Functions workflow enters a wait-and-check loop to monitor job status
5. Once the job completes, results are loaded back to Snowflake
6. Success/failure notifications are sent

## Long-running Job Solution

This architecture specifically addresses the challenge of running entity resolution jobs that take longer than AWS Lambda's 15-minute timeout limit:

- The `process` Lambda function only initiates the job and returns immediately
- A `check_status` Lambda function periodically checks job status
- Step Functions manages the state and handles long-running processes with retry logic
- CloudWatch alarms monitor for failures and long-running executions

## Infrastructure Components

| Component | Purpose |
|-----------|---------|
| Lambda Functions | Extract, Process, Check Status, Load, and Notify steps |
| Step Functions | Orchestrates the entire workflow |
| S3 Bucket | Stores input files and matching results |
| CloudWatch Alarms | Monitors for failures and delays |
| SNS Topic | Delivers notifications |
| IAM Roles | Provides necessary permissions |

## Prerequisites

- Terraform >= 1.0.0
- AWS CLI configured with appropriate permissions
- Snowflake account (if using the Snowflake integration)

## Deployment

1. Update the `terraform.tfvars` file with your specific configuration values
2. Initialize Terraform:
   ```
   terraform init
   ```
3. Review the deployment plan:
   ```
   terraform plan
   ```
4. Apply the configuration:
   ```
   terraform apply
   ```

## Monitoring and Alerts

The solution includes comprehensive monitoring:

- CloudWatch Dashboard with Step Functions execution metrics
- CloudWatch Alarms for failed executions and excessive duration
- Log insights for Lambda functions
- Optional email alerts for failures

## Configuration

Key variables to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| project_name | Name prefix for all resources | "entity-resolution" |
| aws_region | AWS region to deploy to | "us-east-1" |
| s3_bucket_name | Name of S3 bucket for data storage | "entity-resolution-data" |
| pipeline_schedule | How often to run the pipeline | "cron(0 0 * * ? *)" |
| alert_email | Email for notifications (leave empty to disable) | "" |
| er_workflow_name | Entity Resolution workflow name | "entity-matching-workflow" |

For complete configuration options, see the `variables.tf` file.

## Security Considerations

- All resources use least-privilege IAM permissions
- S3 bucket has encryption and public access blocks enabled
- VPC configuration isolates Lambda functions when needed
- Sensitive information stored in AWS Secrets Manager

## Troubleshooting

Common issues and solutions:

1. **Pipeline fails at the ProcessEntityResolution step**:
   - Check Entity Resolution workflow configuration
   - Verify input data format matches the schema

2. **Jobs taking longer than expected**:
   - Review job statistics to identify bottlenecks
   - Consider splitting large input files into smaller batches

3. **Check Status function failing**:
   - Verify correct permissions for Entity Resolution API
   - Check CloudWatch logs for specific error messages

## Contributing

Contributions welcome! Please follow the standard Git workflow:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

Copyright (c) 2023

## Python Package Integration

This Terraform module now uses the `aws_entity_resolution` Python package instead of templates. The package provides a standardized way to interact with AWS Entity Resolution services and includes:

- Configuration management
- Data extraction from Snowflake
- Entity resolution processing
- Loading matched data back to Snowflake
- Notification handling

### Prerequisites

Before deploying this module, you need to:

1. Build the Python package:
   ```bash
   cd /path/to/repository
   poetry build
   ```

2. Ensure the wheel file is available in the `dist/` directory:
   ```
   dist/aws_entity_resolution-0.1.0-py3-none-any.whl
   ```

The Terraform module will automatically:
- Upload the wheel file to S3
- Create a Lambda layer with the package
- Configure Glue jobs to use the package
