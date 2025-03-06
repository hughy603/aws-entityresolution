variable "config" {
  description = "Configuration from the config module"
  type = object({
    resource_prefix = string
    common_tags     = map(string)
    storage = object({
      input_prefix  = string
      output_prefix = string
      data_prefix   = string
      bucket_name   = string
    })
  })
}

variable "enable_versioning" {
  description = "Enable versioning for S3 bucket"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable server-side encryption for S3 bucket"
  type        = bool
  default     = true
}

variable "lifecycle_rules" {
  description = "List of lifecycle rules for S3 bucket"
  type = list(object({
    id                  = string
    prefix              = string
    enabled             = bool
    expiration_days     = optional(number)
    transition_days     = optional(number)
    storage_class       = optional(string)
    noncurrent_versions = optional(number)
  }))
  default = []
}

variable "force_destroy" {
  description = "Allow destruction of non-empty bucket"
  type        = bool
  default     = false
}

variable "existing_bucket_name" {
  description = "Name of an existing S3 bucket to use instead of creating a new one"
  type        = string
  default     = null
}

variable "kms_key_arn" {
  description = "ARN of KMS key to use for S3 bucket encryption"
  type        = string
  default     = null
}
