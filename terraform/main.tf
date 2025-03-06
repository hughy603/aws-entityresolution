terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = var.state_bucket
    key            = "${var.environment}/terraform.tfstate"
    region         = var.aws_region
    dynamodb_table = var.state_lock_table
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.87"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Use Secrets Manager for Snowflake credentials
data "aws_secretsmanager_secret" "snowflake_credentials" {
  name = "snowflake/credentials/${var.environment}"
}

data "aws_secretsmanager_secret_version" "snowflake_credentials" {
  secret_id = data.aws_secretsmanager_secret.snowflake_credentials.id
}

locals {
  snowflake_credentials = jsondecode(data.aws_secretsmanager_secret_version.snowflake_credentials.secret_string)

  common_tags = merge(
    var.default_tags,
    {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
    }
  )
}

provider "snowflake" {
  account  = local.snowflake_credentials.account
  username = local.snowflake_credentials.username
  password = local.snowflake_credentials.password
  role     = local.snowflake_credentials.role
}

# Entity Resolution Pipeline module that encapsulates all functionality
module "entity_resolution_pipeline" {
  source = "./modules/entity-resolution-pipeline"

  # Project configuration
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  # Storage configuration
  storage_config = {
    s3_bucket_name   = var.s3_bucket_name
    s3_input_prefix  = var.s3_input_prefix
    s3_output_prefix = var.s3_output_prefix
  }

  # Support for pre-created resources
  existing_bucket_name = var.existing_bucket_name
  existing_kms_key_arn = var.existing_kms_key_arn

  # Entity Resolution configuration
  er_config = {
    workflow_name     = var.er_workflow_name
    schema_name       = var.er_schema_name
    entity_attributes = var.er_entity_attributes
    schema_definition = var.schema_definition
  }

  # Lambda configuration
  lambda_config = {
    runtime            = var.lambda_runtime
    timeout            = var.lambda_timeout
    memory_size        = var.lambda_memory_size
    layer_arn          = var.lambda_layer_arn
    enable_xray        = var.enable_xray
    log_retention_days = var.log_retention_days
  }

  # Network configuration
  network_config = {
    subnet_ids = var.subnet_ids
    vpc_id     = var.vpc_id
  }

  # Notification configuration
  notification_config = {
    email     = var.notification_email
    topic_arn = var.notification_topic_arn
  }

  # Event trigger configuration
  enable_event_trigger = var.enable_event_trigger
  event_trigger_config = {
    runtime             = var.event_trigger_runtime
    memory_size         = var.event_trigger_memory_size
    timeout             = var.event_trigger_timeout
    enable_s3_trigger   = var.enable_s3_event_trigger
    trigger_bucket_name = var.event_trigger_bucket_name
    trigger_prefix      = var.event_trigger_prefix
  }

  # Snowflake configuration - pass secret ARN instead of credentials
  snowflake_secret_arn = data.aws_secretsmanager_secret.snowflake_credentials.arn

  # Tags
  tags = local.common_tags
}
