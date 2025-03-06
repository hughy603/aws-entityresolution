variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "s3_bucket_name" {
  description = "S3 bucket for data storage"
  type        = string
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

variable "er_workflow_name" {
  description = "Entity Resolution workflow name"
  type        = string
}

variable "er_schema_name" {
  description = "Entity Resolution schema name"
  type        = string
}

variable "er_entity_attributes" {
  description = "List of entity attributes"
  type        = list(string)
}

variable "subnet_ids" {
  description = "List of subnet IDs for VPC deployment"
  type        = list(string)
  default     = []
}

variable "vpc_id" {
  description = "VPC ID for deployment"
  type        = string
  default     = null
}

variable "notification_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  type        = string
  default     = null
}

variable "default_tags" {
  description = "Default tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer containing shared code"
  type        = string
}

variable "schema_definition" {
  description = "Custom schema definition if not using template"
  type = object({
    attributes = list(object({
      name      = string
      type      = string
      sub_type  = optional(string)
      match_key = optional(bool)
      required  = optional(bool)
      array     = optional(bool)
    }))
  })
  default = null
}

variable "notification_email" {
  description = "Email address for receiving error notifications"
  type        = string
  default     = ""
}

variable "snowflake_source_account" {
  description = "Snowflake source account identifier"
  type        = string
}

variable "snowflake_source_username" {
  description = "Snowflake source username"
  type        = string
}

variable "snowflake_source_password" {
  description = "Snowflake source password"
  type        = string
  sensitive   = true
}

variable "snowflake_source_role" {
  description = "Snowflake source role"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_runtime" {
  description = "Runtime for Lambda functions"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions in MB"
  type        = number
  default     = 256
}

variable "enable_xray" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}
