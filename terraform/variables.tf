variable "state_bucket" {
  description = "S3 bucket for Terraform state storage"
  type        = string
}

variable "state_lock_table" {
  description = "DynamoDB table for Terraform state locking"
  type        = string
  default     = "terraform-state-lock"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
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
  default     = {}
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer containing shared code"
  type        = string
  default     = null
}

variable "schema_definition" {
  description = "Custom schema definition for Entity Resolution"
  type = object({
    name              = string
    template_name     = string
    use_template      = bool
    schema_file       = string
    entity_attributes = list(string)
  })
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
  default     = null
}

variable "snowflake_source_account" {
  description = "Snowflake account identifier"
  type        = string
}

variable "snowflake_source_username" {
  description = "Snowflake username"
  type        = string
}

variable "snowflake_source_password" {
  description = "Snowflake password"
  type        = string
  sensitive   = true
}

variable "snowflake_source_role" {
  description = "Snowflake role"
  type        = string
  default     = "ACCOUNTADMIN"
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
  default     = 512
}

variable "enable_xray" {
  description = "Enable X-Ray tracing for Lambda functions"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

# Pre-created resources
variable "existing_bucket_name" {
  description = "Name of an existing S3 bucket to use instead of creating a new one"
  type        = string
  default     = null
}

variable "existing_kms_key_arn" {
  description = "ARN of an existing KMS key to use for encryption"
  type        = string
  default     = null
}

# Event trigger configuration
variable "enable_event_trigger" {
  description = "Whether to create the event trigger Lambda to start Step Functions executions"
  type        = bool
  default     = false
}

variable "event_trigger_runtime" {
  description = "Runtime for the event trigger Lambda"
  type        = string
  default     = "nodejs16.x"
}

variable "event_trigger_memory_size" {
  description = "Memory size for the event trigger Lambda"
  type        = number
  default     = 128
}

variable "event_trigger_timeout" {
  description = "Timeout for the event trigger Lambda"
  type        = number
  default     = 30
}

variable "enable_s3_event_trigger" {
  description = "Whether to enable S3 event triggering via EventBridge"
  type        = bool
  default     = false
}

variable "event_trigger_bucket_name" {
  description = "Name of the S3 bucket to monitor for events (defaults to the primary bucket if not specified)"
  type        = string
  default     = ""
}

variable "event_trigger_prefix" {
  description = "S3 key prefix to monitor for events"
  type        = string
  default     = ""
}
