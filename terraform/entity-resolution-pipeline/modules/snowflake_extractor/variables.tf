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
  description = "Snowflake database containing the source data"
  type        = string
}

variable "snowflake_schema" {
  description = "Snowflake schema containing the source data"
  type        = string
}

variable "source_table" {
  description = "Snowflake table containing the entity data to extract"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket to store extracted entity data"
  type        = string
}

variable "s3_prefix" {
  description = "S3 prefix to use for extracted entity data"
  type        = string
  default     = "input/"
}

variable "aws_region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "us-east-1"
}

variable "entity_attributes" {
  description = "List of entity attributes to extract"
  type        = list(string)
  default     = ["id", "name", "email", "phone", "address", "company"]
}

variable "extraction_glue_job_name" {
  description = "Name of the AWS Glue job for extraction"
  type        = string
  default     = "snowflake-to-s3-extraction"
}

variable "glue_iam_role" {
  description = "IAM role ARN for Glue jobs"
  type        = string
}

variable "extraction_schedule" {
  description = "Cron schedule expression for the extraction job"
  type        = string
  default     = "cron(0 0 * * ? *)" # Default: daily at midnight
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
