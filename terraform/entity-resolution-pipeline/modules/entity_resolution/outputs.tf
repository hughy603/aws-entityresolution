output "entity_resolution_role_arn" {
  description = "ARN of the IAM role for Entity Resolution"
  value       = aws_iam_role.entity_resolution_role.arn
}

output "matching_workflow_arn" {
  description = "ARN of the Entity Resolution matching workflow"
  value       = aws_entityresolution_matching_workflow.entity_matching.arn
}

output "schema_arn" {
  description = "ARN of the Entity Resolution schema mapping"
  value       = aws_entityresolution_schema_mapping.entity_schema.arn
}

output "glue_job_name" {
  description = "Name of the Entity Resolution Glue job"
  value       = aws_glue_job.entity_resolution_processor.name
}

output "glue_job_arn" {
  description = "ARN of the Entity Resolution Glue job"
  value       = aws_glue_job.entity_resolution_processor.arn
}

output "s3_output_path" {
  description = "S3 path where resolved entity data will be stored"
  value       = "s3://${var.s3_bucket}/${var.output_s3_prefix}"
}
