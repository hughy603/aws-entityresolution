variable "config" {
  description = "Configuration from the config module"
  type = object({
    resource_prefix = string
    common_tags     = map(string)
    iam_roles       = map(string)
  })
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for data storage"
  type        = string
}

variable "lambda_functions" {
  description = "Map of Lambda function configurations"
  type = map(object({
    name        = string
    description = string
    permissions = list(string)
  }))
}

variable "enable_vpc_access" {
  description = "Whether to enable VPC access for Lambda functions"
  type        = bool
  default     = false
}

variable "enable_entity_resolution" {
  description = "Whether to enable Entity Resolution service access"
  type        = bool
  default     = true
}
