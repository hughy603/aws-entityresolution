variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "entity_resolution_role_name" {
  description = "Name of the IAM role for Entity Resolution"
  type        = string
  default     = "entity-resolution-service-role"
}

variable "entity_resolution_policy_name" {
  description = "Name of the IAM policy for Entity Resolution"
  type        = string
  default     = "entity-resolution-service-policy"
}

variable "s3_bucket" {
  description = "S3 bucket to store entity data"
  type        = string
}

variable "input_s3_prefix" {
  description = "S3 prefix for input data"
  type        = string
  default     = "input/"
}

variable "output_s3_prefix" {
  description = "S3 prefix for output data"
  type        = string
  default     = "output/"
}

variable "matching_workflow_name" {
  description = "Name of the Entity Resolution matching workflow"
  type        = string
  default     = "entity-matching-workflow"
}

variable "schema_name" {
  description = "Name of the Entity Resolution schema"
  type        = string
  default     = "entity-schema"
}

variable "entity_attributes" {
  description = "List of entity attributes for schema"
  type        = list(string)
  default     = ["id", "name", "email", "phone", "address", "company"]
}

variable "glue_job_name" {
  description = "Name of the AWS Glue job for entity resolution processing"
  type        = string
  default     = "entity-resolution-processor"
}

variable "glue_iam_role" {
  description = "IAM role ARN for Glue jobs"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
