# Project and environment settings
project_name = "aws-entityresolution"
environment  = "dev"
aws_region   = "us-west-2"

# Storage configuration
s3_bucket_name   = "aws-entityresolution-dev-data"
s3_input_prefix  = "input/"
s3_output_prefix = "output/"

# Entity Resolution configuration
er_workflow_name     = "entity-resolution-workflow-dev"
er_schema_name       = "customer-matching-schema-dev"
er_entity_attributes = ["name", "address", "phone", "email"]

# Schema definition
schema_definition = {
  name              = "customer-matching-schema-dev"
  template_name     = "customer-matching"
  use_template      = true
  schema_file       = "schemas/customer-matching.json"
  entity_attributes = ["name", "address", "phone", "email"]
}

# Lambda settings
lambda_runtime     = "python3.9"
lambda_timeout     = 300
lambda_memory_size = 512
lambda_layer_arn   = null # Will be created by CI/CD
enable_xray        = true
log_retention_days = 30

# Network configuration (use VPC in dev for testing)
subnet_ids = []
vpc_id     = null

# Notification settings
notification_email     = "admin-dev@example.com"
notification_topic_arn = null

# Default tags
default_tags = {
  Environment = "dev"
  Project     = "aws-entityresolution"
  Owner       = "data-team"
  CostCenter  = "1234"
}

# State storage
state_bucket     = "aws-entityresolution-terraform-state"
state_lock_table = "terraform-state-lock"

# Snowflake configuration
snowflake_source_account  = "your-snowflake-account-dev"
snowflake_source_username = "snowflake_user"
snowflake_source_password = "dummy-password-replace-with-secrets-manager"
snowflake_source_role     = "ACCOUNTADMIN"
