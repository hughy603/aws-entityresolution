output "s3_bucket_name" {
  description = "Name of the S3 bucket for entity data"
  value       = aws_s3_bucket.entity_resolution_data.bucket
}

output "s3_input_path" {
  description = "S3 path for input data"
  value       = module.snowflake_extractor.s3_input_path
}

output "s3_output_path" {
  description = "S3 path for output data"
  value       = module.entity_resolution.s3_output_path
}

output "entity_resolution_role_arn" {
  description = "ARN of the IAM role for Entity Resolution"
  value       = module.entity_resolution.entity_resolution_role_arn
}

output "glue_role_arn" {
  description = "ARN of the IAM role for Glue jobs"
  value       = aws_iam_role.glue_role.arn
}

output "extraction_glue_job_name" {
  description = "Name of the Glue job for extraction"
  value       = module.snowflake_extractor.glue_job_name
}

output "entity_resolution_glue_job_name" {
  description = "Name of the Glue job for entity resolution processing"
  value       = module.entity_resolution.glue_job_name
}

output "loader_glue_job_name" {
  description = "Name of the Glue job for loading data to Snowflake"
  value       = module.snowflake_loader.glue_job_name
}

output "matching_workflow_arn" {
  description = "ARN of the Entity Resolution matching workflow"
  value       = module.entity_resolution.matching_workflow_arn
}

output "entity_schema_arn" {
  description = "ARN of the Entity Resolution schema mapping"
  value       = module.entity_resolution.schema_arn
}

output "snowflake_target_table" {
  description = "Name of the Snowflake target table for golden records"
  value       = module.snowflake_loader.snowflake_target_table
}

output "snowflake_source_info" {
  description = "Snowflake source information"
  value       = "${var.snowflake_source_database}.${var.snowflake_source_schema}.${var.source_table}"
}

output "snowflake_target_info" {
  description = "Snowflake target information"
  value       = "${var.snowflake_target_database}.${var.snowflake_target_schema}.${var.target_table}"
}
