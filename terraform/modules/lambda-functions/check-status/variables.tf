variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
}

variable "lambda_runtime" {
  description = "Runtime for Lambda functions"
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout" {
  description = "Default timeout for Lambda functions"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Default memory size for Lambda functions"
  type        = number
  default     = 256
}

variable "vpc_config" {
  description = "VPC configuration for Lambda functions"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = {
    subnet_ids         = []
    security_group_ids = []
  }
}

variable "tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer to use"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket configuration"
  type = object({
    name          = string
    input_prefix  = string
    output_prefix = string
  })
}

variable "entity_resolution_config" {
  description = "Entity Resolution configuration"
  type = object({
    workflow_name     = string
    schema_name       = string
    entity_attributes = list(string)
  })
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = null
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
