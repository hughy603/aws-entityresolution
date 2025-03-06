# Entity Resolution Monitoring Module

This module sets up comprehensive monitoring and alerting for the Entity Resolution Pipeline.

## Features

- CloudWatch alarms for:
  - Step Functions execution failures
  - Lambda function errors
  - Lambda function duration thresholds
- Structured logging with metric filters
- Consolidated CloudWatch dashboard
- SNS notifications for alerts

## Usage

```hcl
module "monitoring" {
  source = "./modules/monitoring"

  project_name     = "my-entity-resolution"
  aws_region      = "us-west-2"
  alert_email     = "alerts@example.com"

  lambda_functions = {
    load = {
      function_name = "load-function-name"
      arn          = "load-function-arn"
    }
    process = {
      function_name = "process-function-name"
      arn          = "process-function-arn"
    }
    # ... other functions
  }

  step_function_arn = "step-function-arn"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_name | Name of the project, used as prefix | `string` | n/a | yes |
| aws_region | AWS region for resources | `string` | n/a | yes |
| alert_email | Email for alert notifications | `string` | `""` | no |
| lambda_functions | Map of Lambda function details | `map(object)` | n/a | yes |
| step_function_arn | ARN of Step Functions state machine | `string` | n/a | yes |
| retention_days | CloudWatch log retention days | `number` | `30` | no |
| alarm_evaluation_periods | Periods to evaluate alarms | `number` | `1` | no |
| alarm_period_seconds | Seconds per evaluation period | `number` | `300` | no |
| lambda_timeout_threshold | Lambda duration alarm threshold (ms) | `number` | `45000` | no |

## Outputs

| Name | Description |
|------|-------------|
| sns_topic_arn | ARN of the SNS alerts topic |
| dashboard_name | Name of the CloudWatch dashboard |
| metric_alarms | Map of CloudWatch metric alarms |
| log_metric_filters | Map of log metric filters |

## Dashboard

The module creates a consolidated CloudWatch dashboard with:
- Step Functions execution metrics
- Lambda function metrics (invocations, errors, duration)
- Error log metrics from structured logging

## Alerts

Alerts are sent via SNS when:
- Step Functions executions fail
- Lambda functions encounter errors
- Lambda functions approach their timeout threshold
- Error logs exceed thresholds

## Structured Logging

The module configures metric filters for structured logs with:
- Timestamp
- Request ID
- Log level
- Custom metrics for error tracking
