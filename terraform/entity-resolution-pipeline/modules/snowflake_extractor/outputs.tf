output "glue_job_name" {
  description = "Name of the created Glue job"
  value       = aws_glue_job.snowflake_to_s3.name
}

output "glue_job_arn" {
  description = "ARN of the created Glue job"
  value       = aws_glue_job.snowflake_to_s3.arn
}

output "extraction_trigger_name" {
  description = "Name of the Glue job trigger"
  value       = aws_glue_trigger.snowflake_extraction_schedule.name
}

output "s3_input_path" {
  description = "S3 path where extracted data will be stored"
  value       = "s3://${var.s3_bucket}/${var.s3_prefix}"
}

output "entity_attributes" {
  description = "Entity attributes being extracted"
  value       = var.entity_attributes
}
