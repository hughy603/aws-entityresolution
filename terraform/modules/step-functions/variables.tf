variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
}

variable "lambda_functions" {
  description = "Map of Lambda functions with their details"
  type = map(object({
    function_name = string
    arn           = string
    invoke_arn    = optional(string)
  }))
}

# For backwards compatibility - these will be deprecated
variable "load_data_lambda_arn" {
  description = "[DEPRECATED] ARN of the Lambda function for loading data - use lambda_functions map instead"
  type        = string
  default     = null
}

variable "check_status_lambda_arn" {
  description = "[DEPRECATED] ARN of the Lambda function for checking status - use lambda_functions map instead"
  type        = string
  default     = null
}

variable "process_output_lambda_arn" {
  description = "[DEPRECATED] ARN of the Lambda function for processing output - use lambda_functions map instead"
  type        = string
  default     = null
}

variable "notify_lambda_arn" {
  description = "[DEPRECATED] ARN of the Lambda function for notifications - use lambda_functions map instead"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "default_tags" {
  description = "Default tags to be applied to all resources"
  type        = map(string)
  default     = {}
}

variable "error_notification_config" {
  description = "Configuration for error notifications"
  type = object({
    enabled       = bool
    sns_topic_arn = string
  })
  default = {
    enabled       = false
    sns_topic_arn = null
  }
}

variable "workflow_config" {
  description = "Configuration for the Entity Resolution workflow"
  type = object({
    max_concurrent_executions = optional(number, 1)
    execution_timeout_minutes = optional(number, 60)
    retry_attempts            = optional(number, 3)
    retry_interval_seconds    = optional(number, 60)
  })
  default = {}
}
