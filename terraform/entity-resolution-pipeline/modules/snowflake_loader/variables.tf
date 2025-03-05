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

variable "snowflake_database" {
  description = "Snowflake database to load resolved data into"
  type        = string
}

variable "snowflake_schema" {
  description = "Snowflake schema to load resolved data into"
  type        = string
}

variable "target_table" {
  description = "Snowflake table to load resolved entity data into"
  type        = string
  default     = "GOLDEN_ENTITY_RECORDS"
}

variable "s3_bucket" {
  description = "S3 bucket containing the resolved entity data"
  type        = string
}

variable "s3_output_prefix" {
  description = "S3 prefix where resolved entity data is stored"
  type        = string
  default     = "output/"
}

variable "aws_region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "us-east-1"
}

variable "entity_attributes" {
  description = "List of entity attributes to load"
  type        = list(string)
  default     = ["id", "name", "email", "phone", "address", "company"]
}

variable "loader_glue_job_name" {
  description = "Name of the AWS Glue job for loading data to Snowflake"
  type        = string
  default     = "s3-to-snowflake-loader"
}

variable "glue_iam_role" {
  description = "IAM role ARN for Glue jobs"
  type        = string
}

variable "loading_schedule" {
  description = "Cron schedule expression for the loading job"
  type        = string
  default     = "cron(0 1 * * ? *)" # Default: daily at 1am (1 hour after extraction)
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
