# ---------------------------------------------------------------------------------------------------------------------
# REQUIRED VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "project_name" {
  description = "Name of the project, used as a prefix for all resources"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
}

# ---------------------------------------------------------------------------------------------------------------------
# OPTIONAL VARIABLES WITH DEFAULTS
# ---------------------------------------------------------------------------------------------------------------------

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "resource_tags" {
  description = "Additional resource-specific tags"
  type        = map(string)
  default     = {}
}

variable "lambda_config" {
  description = "Lambda function configuration"
  type = object({
    memory_size = number
    timeout     = number
  })
  default = {
    memory_size = 256
    timeout     = 60
  }
}

variable "monitoring_config" {
  description = "Monitoring and alerting configuration"
  type = object({
    log_retention_days = number
    error_threshold    = number
    warning_threshold  = number
  })
  default = {
    log_retention_days = 30
    error_threshold    = 1
    warning_threshold  = 3
  }
}

variable "storage_config" {
  description = "Storage configuration for S3 buckets"
  type = object({
    input_prefix  = string
    output_prefix = string
    data_prefix   = string
  })
  default = {
    input_prefix  = "input/"
    output_prefix = "output/"
    data_prefix   = "data/"
  }
}

variable "entity_resolution_config" {
  description = "Entity Resolution service configuration"
  type = object({
    matching_threshold     = number
    max_matches_per_record = number
  })
  default = {
    matching_threshold     = 0.85
    max_matches_per_record = 10
  }
  validation {
    condition     = var.entity_resolution_config.matching_threshold >= 0.0 && var.entity_resolution_config.matching_threshold <= 1.0
    error_message = "Matching threshold must be between 0.0 and 1.0."
  }
  validation {
    condition     = var.entity_resolution_config.max_matches_per_record > 0 && var.entity_resolution_config.max_matches_per_record <= 100
    error_message = "Max matches per record must be between 1 and 100."
  }
}
