variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "entity-resolution"
    ManagedBy   = "terraform"
  }
}

variable "resource_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "Name of the S3 bucket for entity data"
  type        = string
  default     = "entity-resolution-data"
}

variable "s3_input_prefix" {
  description = "S3 prefix for input data"
  type        = string
  default     = "input/"
}

variable "s3_output_prefix" {
  description = "S3 prefix for output data"
  type        = string
  default     = "output/"
}

# Snowflake Configuration
variable "snowflake_account" {
  description = "Snowflake account identifier"
  type        = string
}

variable "snowflake_username" {
  description = "Snowflake username"
  type        = string
}

variable "snowflake_password" {
  description = "Snowflake password"
  type        = string
  sensitive   = true
}

variable "snowflake_role" {
  description = "Snowflake role to use"
  type        = string
  default     = "ACCOUNTADMIN"
}

variable "snowflake_warehouse" {
  description = "Snowflake warehouse to use"
  type        = string
}

variable "snowflake_source_database" {
  description = "Snowflake database containing the source data"
  type        = string
}

variable "snowflake_source_schema" {
  description = "Snowflake schema containing the source data"
  type        = string
}

variable "snowflake_target_database" {
  description = "Snowflake database to load resolved data into"
  type        = string
}

variable "snowflake_target_schema" {
  description = "Snowflake schema to load resolved data into"
  type        = string
}

variable "source_table" {
  description = "Snowflake table containing the entity data to extract"
  type        = string
}

variable "target_table" {
  description = "Snowflake table to load resolved entity data into"
  type        = string
  default     = "GOLDEN_ENTITY_RECORDS"
}

# Entity Resolution Configuration
variable "entity_resolution_role_name" {
  description = "Name of the IAM role for Entity Resolution"
  type        = string
  default     = "entity-resolution-service-role"
}

variable "matching_workflow_name" {
  description = "Name of the Entity Resolution matching workflow"
  type        = string
  default     = "entity-matching-workflow"
}

variable "schema_name" {
  description = "Name of the Entity Resolution schema"
  type        = string
  default     = "entity-schema"
}

variable "entity_attributes" {
  description = "List of entity attributes to extract, process, and load"
  type        = list(string)
  default     = ["id", "name", "email", "phone", "address", "company"]
}

# Glue Configuration
variable "glue_iam_role_name" {
  description = "Name of the IAM role for Glue jobs"
  type        = string
  default     = "entity-resolution-glue-role"
}

variable "extraction_glue_job_name" {
  description = "Name of the AWS Glue job for extraction"
  type        = string
  default     = "snowflake-to-s3-extraction"
}

variable "entity_resolution_glue_job_name" {
  description = "Name of the AWS Glue job for entity resolution processing"
  type        = string
  default     = "entity-resolution-processor"
}

variable "loader_glue_job_name" {
  description = "Name of the AWS Glue job for loading data to Snowflake"
  type        = string
  default     = "s3-to-snowflake-loader"
}

variable "extraction_schedule" {
  description = "Cron schedule expression for the extraction job"
  type        = string
  default     = "cron(0 0 * * ? *)" # Default: daily at midnight
}

variable "loading_schedule" {
  description = "Cron schedule expression for the loading job"
  type        = string
  default     = "cron(0 1 * * ? *)" # Default: daily at 1am (1 hour after extraction)
}

variable "entity_resolution_dashboard_url" {
  description = "URL for the Entity Resolution dashboard in Splunk or Dynatrace"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email address to send alerts to (leave empty to disable email notifications)"
  type        = string
  default     = ""
}
