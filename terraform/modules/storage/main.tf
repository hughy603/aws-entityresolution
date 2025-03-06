locals {
  default_lifecycle_rules = [
    {
      id              = "archive-old-data"
      prefix          = "${var.config.storage.data_prefix}archive/"
      enabled         = true
      transition_days = 90
      storage_class   = "GLACIER"
    }
  ]

  all_lifecycle_rules = concat(local.default_lifecycle_rules, var.lifecycle_rules)

  # Determine whether to create a new bucket or use an existing one
  create_bucket = var.existing_bucket_name == null || var.existing_bucket_name == ""

  # Use the provided bucket name or the existing bucket name
  bucket_name = local.create_bucket ? var.config.storage.bucket_name : var.existing_bucket_name
}

# Get current region
data "aws_region" "current" {}

# Main data bucket - only created if existing_bucket_name is not provided
resource "aws_s3_bucket" "data" {
  count         = local.create_bucket ? 1 : 0
  bucket        = var.config.storage.bucket_name
  force_destroy = var.force_destroy

  tags = var.config.common_tags
}

# Use data source for existing bucket if provided
data "aws_s3_bucket" "existing" {
  count  = local.create_bucket ? 0 : 1
  bucket = var.existing_bucket_name
}

# Determine the bucket ID to use (either newly created or existing)
locals {
  bucket_id  = local.create_bucket ? aws_s3_bucket.data[0].id : data.aws_s3_bucket.existing[0].id
  bucket_arn = local.create_bucket ? aws_s3_bucket.data[0].arn : data.aws_s3_bucket.existing[0].arn
}

# Bucket versioning - only applied to newly created buckets
resource "aws_s3_bucket_versioning" "data" {
  count  = local.create_bucket && var.enable_versioning ? 1 : 0
  bucket = local.bucket_id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption - only applied to newly created buckets
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  count = local.create_bucket && var.enable_encryption ? 1 : 0

  bucket = local.bucket_id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

# Public access block - only applied to newly created buckets
resource "aws_s3_bucket_public_access_block" "data" {
  count  = local.create_bucket ? 1 : 0
  bucket = local.bucket_id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules - only applied to newly created buckets
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  count  = local.create_bucket ? 1 : 0
  bucket = local.bucket_id

  dynamic "rule" {
    for_each = local.all_lifecycle_rules

    content {
      id     = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"

      filter {
        prefix = rule.value.prefix
      }

      dynamic "transition" {
        for_each = rule.value.transition_days != null ? [1] : []
        content {
          days          = rule.value.transition_days
          storage_class = rule.value.storage_class
        }
      }

      dynamic "expiration" {
        for_each = rule.value.expiration_days != null ? [1] : []
        content {
          days = rule.value.expiration_days
        }
      }

      dynamic "noncurrent_version_expiration" {
        for_each = rule.value.noncurrent_versions != null ? [1] : []
        content {
          noncurrent_days = rule.value.noncurrent_versions
        }
      }
    }
  }
}

# Input prefix object - creates an empty object to maintain prefix
resource "aws_s3_object" "input_prefix" {
  bucket  = local.bucket_id
  key     = "${var.config.storage.input_prefix}.keep"
  content = "This file maintains the input prefix structure"
}

# Output prefix object - creates an empty object to maintain prefix
resource "aws_s3_object" "output_prefix" {
  bucket  = local.bucket_id
  key     = "${var.config.storage.output_prefix}.keep"
  content = "This file maintains the output prefix structure"
}

# Data prefix object - creates an empty object to maintain prefix
resource "aws_s3_object" "data_prefix" {
  bucket  = local.bucket_id
  key     = "${var.config.storage.data_prefix}.keep"
  content = "This file maintains the data prefix structure"
}
