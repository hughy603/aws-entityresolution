variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. dev, test, prod)"
  type        = string
}

variable "enabled" {
  description = "Whether to create the event trigger Lambda function"
  type        = bool
  default     = true
}

variable "runtime" {
  description = "Lambda runtime to use"
  type        = string
  default     = "nodejs16.x"
}

variable "memory_size" {
  description = "Lambda memory size"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Lambda timeout"
  type        = number
  default     = 30
}

variable "step_function_arn" {
  description = "ARN of the Step Functions state machine to trigger"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain Lambda logs"
  type        = number
  default     = 14
}

variable "vpc_config" {
  description = "VPC configuration for the Lambda function"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "enable_s3_trigger" {
  description = "Whether to enable S3 event triggering via EventBridge"
  type        = bool
  default     = false
}

variable "trigger_bucket_name" {
  description = "Name of the S3 bucket to monitor for events"
  type        = string
  default     = ""
}

variable "trigger_prefix" {
  description = "S3 key prefix to monitor for events"
  type        = string
  default     = ""
}
