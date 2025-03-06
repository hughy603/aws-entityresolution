variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

# Storage configuration group
variable "storage_config" {
  description = "Storage configuration for S3"
  type = object({
    s3_bucket_name   = string
    s3_input_prefix  = string
    s3_output_prefix = string
  })
}

# Entity Resolution configuration group
variable "er_config" {
  description = "Entity Resolution configuration"
  type = object({
    workflow_name     = string
    schema_name       = string
    entity_attributes = list(string)
    schema_definition = object({
      name              = string
      template_name     = string
      use_template      = bool
      schema_file       = string
      entity_attributes = list(string)
    })
  })
}

# Network configuration group
variable "network_config" {
  description = "Network configuration for VPC deployment"
  type = object({
    subnet_ids = list(string)
    vpc_id     = string
  })
  default = {
    subnet_ids = []
    vpc_id     = null
  }
}

# Notification configuration group
variable "notification_config" {
  description = "Notification configuration"
  type = object({
    email     = string
    topic_arn = string
  })
  default = {
    email     = null
    topic_arn = null
  }
}

# Lambda configuration group
variable "lambda_config" {
  description = "Lambda function configuration"
  type = object({
    runtime            = string
    timeout            = number
    memory_size        = number
    layer_arn          = string
    enable_xray        = bool
    log_retention_days = number
  })
  default = {
    runtime            = "python3.9"
    timeout            = 300
    memory_size        = 512
    layer_arn          = null
    enable_xray        = false
    log_retention_days = 30
  }
}

# Snowflake secret ARN
variable "snowflake_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Snowflake credentials"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# For backwards compatibility - these will be deprecated
variable "s3_bucket_name" {
  description = "[DEPRECATED] S3 bucket for data storage - use storage_config instead"
  type        = string
  default     = null
}

variable "s3_input_prefix" {
  description = "[DEPRECATED] S3 prefix for input data - use storage_config instead"
  type        = string
  default     = "input/"
}

variable "s3_output_prefix" {
  description = "[DEPRECATED] S3 prefix for output data - use storage_config instead"
  type        = string
  default     = "output/"
}

variable "er_workflow_name" {
  description = "[DEPRECATED] Entity Resolution workflow name - use er_config instead"
  type        = string
  default     = null
}

variable "er_schema_name" {
  description = "[DEPRECATED] Entity Resolution schema name - use er_config instead"
  type        = string
  default     = null
}

variable "er_entity_attributes" {
  description = "[DEPRECATED] List of entity attributes - use er_config instead"
  type        = list(string)
  default     = null
}

variable "schema_definition" {
  description = "[DEPRECATED] Custom schema definition for Entity Resolution - use er_config instead"
  type = object({
    name              = string
    template_name     = string
    use_template      = bool
    schema_file       = string
    entity_attributes = list(string)
  })
  default = null
}

variable "subnet_ids" {
  description = "[DEPRECATED] List of subnet IDs for VPC deployment - use network_config instead"
  type        = list(string)
  default     = []
}

variable "vpc_id" {
  description = "[DEPRECATED] VPC ID for deployment - use network_config instead"
  type        = string
  default     = null
}

variable "notification_email" {
  description = "[DEPRECATED] Email address for notifications - use notification_config instead"
  type        = string
  default     = null
}

variable "notification_topic_arn" {
  description = "[DEPRECATED] ARN of the SNS topic for notifications - use notification_config instead"
  type        = string
  default     = null
}

variable "lambda_runtime" {
  description = "[DEPRECATED] Runtime for Lambda functions - use lambda_config instead"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "[DEPRECATED] Timeout for Lambda functions in seconds - use lambda_config instead"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "[DEPRECATED] Memory size for Lambda functions in MB - use lambda_config instead"
  type        = number
  default     = 512
}

variable "lambda_layer_arn" {
  description = "[DEPRECATED] ARN of the Lambda layer containing shared code - use lambda_config instead"
  type        = string
  default     = null
}

variable "enable_xray" {
  description = "[DEPRECATED] Enable X-Ray tracing for Lambda functions - use lambda_config instead"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "[DEPRECATED] Number of days to retain CloudWatch logs - use lambda_config instead"
  type        = number
  default     = 30
}

variable "snowflake_source_account" {
  description = "[DEPRECATED] Snowflake account identifier - use snowflake_secret_arn instead"
  type        = string
  default     = null
}

variable "snowflake_source_username" {
  description = "[DEPRECATED] Snowflake username - use snowflake_secret_arn instead"
  type        = string
  default     = null
}

variable "snowflake_source_password" {
  description = "[DEPRECATED] Snowflake password - use snowflake_secret_arn instead"
  type        = string
  sensitive   = true
  default     = null
}

variable "snowflake_source_role" {
  description = "[DEPRECATED] Snowflake role - use snowflake_secret_arn instead"
  type        = string
  default     = "ACCOUNTADMIN"
}

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

variable "enable_event_trigger" {
  description = "Whether to create the event trigger Lambda to start Step Functions executions"
  type        = bool
  default     = false
}

variable "event_trigger_config" {
  description = "Configuration for the event trigger Lambda"
  type = object({
    runtime             = optional(string, "nodejs16.x")
    memory_size         = optional(number, 128)
    timeout             = optional(number, 30)
    enable_s3_trigger   = optional(bool, false)
    trigger_bucket_name = optional(string, "")
    trigger_prefix      = optional(string, "")
  })
  default = {}
}
