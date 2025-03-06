output "resource_prefix" {
  description = "Standard prefix for resource names"
  value       = local.resource_prefix
}

output "common_tags" {
  description = "Common tags to be applied to all resources"
  value       = local.common_tags
}

output "lambda" {
  description = "Lambda function configuration"
  value       = local.lambda
}

output "monitoring" {
  description = "Monitoring and alerting configuration"
  value       = local.monitoring
}

output "storage" {
  description = "Storage configuration"
  value       = local.storage
}

output "entity_resolution" {
  description = "Entity Resolution configuration"
  value       = local.entity_resolution
}

output "iam_roles" {
  description = "IAM role name patterns"
  value       = local.iam_roles
}

output "log_groups" {
  description = "CloudWatch log group patterns"
  value       = local.log_groups
}
