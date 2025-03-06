variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
}

variable "tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {}
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
