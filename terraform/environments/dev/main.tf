terraform {
  required_version = ">= 1.0.0"

  backend "s3" {
    bucket         = "aws-entityresolution-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
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
    tags = local.tags
  }
}

provider "snowflake" {
  account  = var.snowflake_source_account
  username = var.snowflake_source_username
  password = var.snowflake_source_password
  role     = var.snowflake_source_role
}

# Import shared configurations
module "common" {
  source = "../../modules/common"

  aws_region                = var.aws_region
  tags                      = local.tags
  snowflake_source_account  = var.snowflake_source_account
  snowflake_source_username = var.snowflake_source_username
  snowflake_source_password = var.snowflake_source_password
  snowflake_source_role     = var.snowflake_source_role
}

# Core configuration module
module "config" {
  source = "../../modules/config"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

# Storage module for S3 and Glue resources
module "storage" {
  source = "../../modules/storage"

  config = {
    project_name  = var.project_name
    environment   = var.environment
    bucket_name   = var.s3_bucket_name
    input_prefix  = var.s3_input_prefix
    output_prefix = var.s3_output_prefix
    tags          = local.tags
  }
}

# Schema management module
module "schema" {
  source = "../../modules/schema"

  config = {
    project_name = var.project_name
    environment  = var.environment
    tags         = local.tags
  }

  schema_definition = {
    name              = var.schema_definition.name
    template_name     = var.schema_definition.template_name
    use_template      = var.schema_definition.use_template
    schema_file       = var.schema_definition.schema_file
    entity_attributes = var.schema_definition.entity_attributes
  }
}

# Lambda functions module
module "lambda_functions" {
  source = "../../modules/lambda-functions"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  lambda_runtime     = var.lambda_runtime
  lambda_timeout     = var.lambda_timeout
  lambda_memory_size = var.lambda_memory_size
  lambda_layer_arn   = var.lambda_layer_arn
  vpc_config = {
    subnet_ids         = var.subnet_ids
    security_group_ids = [module.security.lambda_security_group_id]
  }
  s3_bucket = {
    name          = module.storage.bucket_id
    input_prefix  = var.s3_input_prefix
    output_prefix = var.s3_output_prefix
  }
  entity_resolution_config = {
    workflow_name     = var.er_workflow_name
    schema_name       = module.schema.schema_name
    entity_attributes = var.er_entity_attributes
  }
  kms_key_arn        = module.security.kms_key_arn
  enable_xray        = var.enable_xray
  log_retention_days = var.log_retention_days
  tags               = local.tags

  depends_on = [module.storage, module.schema, module.security]
}

# Step Functions module
module "step_functions" {
  source = "../../modules/step-functions"

  project_name = var.project_name
  aws_region   = var.aws_region

  # Lambda function ARNs
  load_data_lambda_arn      = module.lambda_functions.load_data.arn
  check_status_lambda_arn   = module.lambda_functions.check_status.arn
  process_output_lambda_arn = module.lambda_functions.process_data.arn
  notify_lambda_arn         = module.lambda_functions.notify.arn

  # Lambda functions map (required by module)
  lambda_functions = {
    load_data = {
      function_name = module.lambda_functions.load_data.function_name
      arn           = module.lambda_functions.load_data.arn
    }
    check_status = {
      function_name = module.lambda_functions.check_status.function_name
      arn           = module.lambda_functions.check_status.arn
    }
    process_output = {
      function_name = module.lambda_functions.process_data.function_name
      arn           = module.lambda_functions.process_data.arn
    }
    notify = {
      function_name = module.lambda_functions.notify.function_name
      arn           = module.lambda_functions.notify.arn
    }
  }

  # Error notification
  error_notification_config = {
    enabled       = var.environment == "prod"
    sns_topic_arn = var.notification_topic_arn
  }

  # Default tags
  default_tags = local.tags

  depends_on = [module.lambda_functions, module.monitoring]
}

# Security module
module "security" {
  source = "../../modules/security"

  config = {
    resource_prefix = "${var.project_name}-${var.environment}"
    common_tags     = local.tags
    iam_roles       = {}
  }
  s3_bucket_name = module.storage.bucket_id
  lambda_functions = {
    for name, fn in module.lambda_functions.function_names : name => {
      name        = fn
      description = "Lambda function for ${name}"
      permissions = ["s3:*", "logs:*"]
    }
  }
  enable_vpc_access        = length(var.subnet_ids) > 0
  enable_entity_resolution = true
}

# Monitoring module
module "monitoring" {
  source = "../../modules/monitoring"

  project_name = var.project_name
  aws_region   = var.aws_region
  alert_email  = var.notification_email
  default_tags = local.tags

  # Lambda functions for monitoring
  lambda_functions = {
    check_status = {
      function_name = module.lambda_functions.check_status.function_name
      arn           = module.lambda_functions.check_status.arn
    }
    load_data = {
      function_name = module.lambda_functions.load_data.function_name
      arn           = module.lambda_functions.load_data.arn
    }
    process_data = {
      function_name = module.lambda_functions.process_data.function_name
      arn           = module.lambda_functions.process_data.arn
    }
    notify = {
      function_name = module.lambda_functions.notify.function_name
      arn           = module.lambda_functions.notify.arn
    }
  }

  step_function_arn = module.step_functions.state_machine_arn
}
