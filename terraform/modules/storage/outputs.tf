output "bucket" {
  description = "S3 bucket details"
  value = {
    name   = local.bucket_id
    arn    = local.bucket_arn
    region = data.aws_region.current.name
  }
}

output "bucket_id" {
  description = "S3 bucket ID"
  value       = local.bucket_id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = local.bucket_arn
}

output "prefixes" {
  description = "S3 bucket prefixes"
  value = {
    input  = var.config.storage.input_prefix
    output = var.config.storage.output_prefix
    data   = var.config.storage.data_prefix
  }
}

output "versioning_enabled" {
  description = "Whether versioning is enabled for the bucket"
  value       = var.enable_versioning
}

output "encryption_enabled" {
  description = "Whether encryption is enabled for the bucket"
  value       = var.enable_encryption
}

output "lifecycle_rules" {
  description = "Active lifecycle rules for the bucket"
  value       = local.all_lifecycle_rules
}

output "is_existing_bucket" {
  description = "Whether an existing bucket was used"
  value       = !local.create_bucket
}
