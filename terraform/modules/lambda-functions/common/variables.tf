variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
}

variable "tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {}
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

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = null
}

variable "s3_bucket" {
  description = "S3 bucket configuration"
  type = object({
    name          = string
    input_prefix  = string
    output_prefix = string
  })
}
