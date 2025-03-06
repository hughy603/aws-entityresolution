locals {
  resource_prefix = "${var.project_name}-${var.environment}"

  # Default configurations with fallbacks for backward compatibility
  storage = {
    bucket_name   = var.storage_config != null ? var.storage_config.s3_bucket_name : var.s3_bucket_name
    input_prefix  = var.storage_config != null ? var.storage_config.s3_input_prefix : var.s3_input_prefix
    output_prefix = var.storage_config != null ? var.storage_config.s3_output_prefix : var.s3_output_prefix
  }

  # Entity Resolution configuration without relying on Python-generated config
  entity_resolution = {
    workflow_name     = var.er_config != null ? var.er_config.workflow_name : var.er_workflow_name
    schema_name       = var.er_config != null ? var.er_config.schema_name : var.er_schema_name
    schema_definition = var.er_config != null ? var.er_config.schema_definition : var.schema_definition
  }

  network = {
    subnet_ids = var.network_config != null ? var.network_config.subnet_ids : var.subnet_ids
    vpc_id     = var.network_config != null ? var.network_config.vpc_id : var.vpc_id
  }

  notification = {
    email     = var.notification_config != null ? var.notification_config.email : var.notification_email
    topic_arn = var.notification_config != null ? var.notification_config.topic_arn : var.notification_topic_arn
  }

  lambda = {
    runtime            = var.lambda_config != null ? var.lambda_config.runtime : var.lambda_runtime
    timeout            = var.lambda_config != null ? var.lambda_config.timeout : var.lambda_timeout
    memory_size        = var.lambda_config != null ? var.lambda_config.memory_size : var.lambda_memory_size
    layer_arn          = var.lambda_config != null ? var.lambda_config.layer_arn : var.lambda_layer_arn
    enable_xray        = var.lambda_config != null ? var.lambda_config.enable_xray : var.enable_xray
    log_retention_days = var.lambda_config != null ? var.lambda_config.log_retention_days : var.log_retention_days
  }
}

# Storage module for S3 and Glue resources
module "storage" {
  source = "../storage"

  config = {
    project_name  = var.project_name
    environment   = var.environment
    bucket_name   = local.storage.bucket_name
    input_prefix  = local.storage.input_prefix
    output_prefix = local.storage.output_prefix
    tags          = var.tags
  }

  # Support for pre-created resources
  existing_bucket_name = var.existing_bucket_name
  kms_key_arn          = var.existing_kms_key_arn
}

# Schema management module - the single source of truth for Entity Resolution schema
module "schema" {
  source = "../schema"

  config = {
    project_name    = var.project_name
    environment     = var.environment
    resource_prefix = local.resource_prefix
    entity_resolution = {
      schema_name   = local.entity_resolution.schema_name
      workflow_name = local.entity_resolution.workflow_name
    }
    tags = var.tags
  }

  schema_definition = local.entity_resolution.schema_definition
}

# Retrieve schema information from SSM parameter
data "aws_ssm_parameter" "schema_parameter" {
  name       = "/${var.project_name}/${var.environment}/entity-resolution/schema"
  depends_on = [module.schema]
}

locals {
  # Parse schema data from SSM parameter (created by schema module)
  schema_data = jsondecode(data.aws_ssm_parameter.schema_parameter.value)

  # Extract attribute names for lambda parameters
  schema_attribute_names = join(",", [
    for attr in local.schema_data.attributes : attr.name
  ])
}

# Security module
module "security" {
  source = "../security"

  config = {
    resource_prefix = local.resource_prefix
    common_tags     = var.tags
    iam_roles       = {}
  }
  s3_bucket_name           = module.storage.bucket_id
  lambda_functions         = {} # Will be updated later after Lambda functions are created
  enable_vpc_access        = length(local.network.subnet_ids) > 0
  enable_entity_resolution = true

  # Lambda functions will be passed after they're created
  depends_on = [module.storage]
}

# Use Secrets Manager for Snowflake credentials
data "aws_secretsmanager_secret_version" "snowflake_credentials" {
  secret_id = var.snowflake_secret_arn
}

locals {
  snowflake_credentials = jsondecode(data.aws_secretsmanager_secret_version.snowflake_credentials.secret_string)
}

# Lambda functions module
module "lambda_functions" {
  source = "../lambda-functions"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  lambda_runtime     = local.lambda.runtime
  lambda_timeout     = local.lambda.timeout
  lambda_memory_size = local.lambda.memory_size
  lambda_layer_arn   = local.lambda.layer_arn
  vpc_config = {
    subnet_ids         = local.network.subnet_ids
    security_group_ids = [module.security.lambda_security_group_id]
  }
  s3_bucket = {
    name          = module.storage.bucket_id
    input_prefix  = local.storage.input_prefix
    output_prefix = local.storage.output_prefix
  }
  entity_resolution_config = {
    workflow_name     = local.entity_resolution.workflow_name
    schema_name       = local.entity_resolution.schema_name
    schema_arn        = local.schema_data.schema_arn
    entity_attributes = local.schema_attribute_names # Use attribute names from parsed schema
  }
  kms_key_arn        = module.security.kms_key_arn
  enable_xray        = local.lambda.enable_xray
  log_retention_days = local.lambda.log_retention_days
  tags               = var.tags

  depends_on = [module.storage, module.schema, module.security]
}

# Step Functions module
module "step_functions" {
  source = "../step-functions"

  project_name = var.project_name
  aws_region   = var.aws_region

  # Pass all lambda functions as a single map
  lambda_functions = module.lambda_functions.functions

  # Error notification
  error_notification_config = {
    enabled       = var.environment == "prod"
    sns_topic_arn = local.notification.topic_arn
  }

  # Default tags
  default_tags = var.tags

  depends_on = [module.lambda_functions]
}

# Optional Event Trigger Lambda
module "event_trigger" {
  source = "../event-trigger"
  count  = var.enable_event_trigger ? 1 : 0

  project_name      = var.project_name
  environment       = var.environment
  enabled           = true
  step_function_arn = module.step_functions.state_machine_arn

  # Use either the pre-created bucket or the newly created one for trigger
  trigger_bucket_name = var.existing_bucket_name != null ? var.existing_bucket_name : module.storage.bucket_id

  # Pass config values
  runtime           = var.event_trigger_config.runtime
  memory_size       = var.event_trigger_config.memory_size
  timeout           = var.event_trigger_config.timeout
  enable_s3_trigger = var.event_trigger_config.enable_s3_trigger
  trigger_prefix    = var.event_trigger_config.trigger_prefix

  # Networking (optional)
  vpc_config = length(local.network.subnet_ids) > 0 ? {
    subnet_ids         = local.network.subnet_ids
    security_group_ids = [module.security.lambda_security_group_id]
  } : null

  # Logging
  log_retention_days = local.lambda.log_retention_days

  # Tags
  tags = var.tags

  depends_on = [module.step_functions]
}

# Monitoring module
module "monitoring" {
  source = "../monitoring"

  project_name = var.project_name
  aws_region   = var.aws_region
  alert_email  = local.notification.email
  default_tags = var.tags

  # Lambda functions for monitoring - use common map structure
  lambda_functions = module.lambda_functions.functions

  step_function_arn = module.step_functions.state_machine_arn
}
