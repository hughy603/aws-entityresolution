variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
}

variable "alert_email" {
  description = "Email address to send alert notifications"
  type        = string
  default     = null
}

variable "lambda_functions" {
  description = "Map of Lambda functions with their details"
  type = map(object({
    function_name = string
    arn           = string
    invoke_arn    = optional(string)
  }))
}

variable "step_function_arn" {
  description = "ARN of the Step Functions state machine"
  type        = string
}

variable "default_tags" {
  description = "Default tags to be applied to all resources"
  type        = map(string)
  default     = {}
}

variable "retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "alarm_evaluation_periods" {
  description = "Number of periods to evaluate for alarm conditions"
  type        = number
  default     = 1
}

variable "alarm_period_seconds" {
  description = "Period in seconds over which to evaluate alarms"
  type        = number
  default     = 300
}

variable "lambda_timeout_threshold" {
  description = "Threshold in milliseconds for Lambda duration alarms"
  type        = number
  default     = 45000 # 45 seconds (75% of 60s default timeout)
}
