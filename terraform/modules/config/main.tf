locals {
  # Resource naming and tagging
  resource_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(
    var.default_tags,
    var.resource_tags,
    {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
    }
  )

  # Lambda configuration with timeout thresholds
  lambda = {
    memory_size        = var.lambda_config.memory_size
    timeout            = var.lambda_config.timeout
    duration_threshold = floor(var.lambda_config.timeout * 0.75) * 1000 # 75% of timeout in milliseconds
  }

  # Monitoring configuration
  monitoring = {
    log_retention_days = var.monitoring_config.log_retention_days
    alert_thresholds = {
      error   = var.monitoring_config.error_threshold
      warning = var.monitoring_config.warning_threshold
    }
    evaluation_periods = 1
    period_seconds     = 300
  }

  # Storage configuration
  storage = {
    input_prefix  = var.storage_config.input_prefix
    output_prefix = var.storage_config.output_prefix
    data_prefix   = var.storage_config.data_prefix
    bucket_name   = "${local.resource_prefix}-data"
  }

  # Entity Resolution configuration
  entity_resolution = {
    matching_threshold     = var.entity_resolution_config.matching_threshold
    max_matches_per_record = var.entity_resolution_config.max_matches_per_record
    workflow_name          = "${local.resource_prefix}-workflow"
    schema_name            = "${local.resource_prefix}-schema"
  }

  # IAM role name patterns
  iam_roles = {
    lambda         = "${local.resource_prefix}-lambda"
    step_functions = "${local.resource_prefix}-step-functions"
    glue           = "${local.resource_prefix}-glue"
  }

  # CloudWatch log group patterns
  log_groups = {
    lambda         = "/aws/lambda/${local.resource_prefix}"
    step_functions = "/aws/step-functions/${local.resource_prefix}"
    glue           = "/aws/glue/${local.resource_prefix}"
  }
}
