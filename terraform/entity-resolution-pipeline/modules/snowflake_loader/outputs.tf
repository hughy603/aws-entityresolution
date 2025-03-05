output "glue_job_name" {
  description = "Name of the created Glue job"
  value       = aws_glue_job.s3_to_snowflake.name
}

output "glue_job_arn" {
  description = "ARN of the created Glue job"
  value       = aws_glue_job.s3_to_snowflake.arn
}

output "loading_trigger_name" {
  description = "Name of the Glue job trigger"
  value       = aws_glue_trigger.snowflake_loading_schedule.name
}

output "snowflake_target_table" {
  description = "Name of the Snowflake target table"
  value       = snowflake_table.golden_records.name
}

output "snowflake_database" {
  description = "Snowflake database containing the target table"
  value       = var.snowflake_database
}

output "snowflake_schema" {
  description = "Snowflake schema containing the target table"
  value       = var.snowflake_schema
}
