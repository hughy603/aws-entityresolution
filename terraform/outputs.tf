output "pipeline" {
  description = "Entity Resolution pipeline outputs"
  value       = module.entity_resolution_pipeline
}

output "s3_bucket" {
  description = "S3 bucket for data storage"
  value       = module.entity_resolution_pipeline.s3_bucket
}

output "lambda_functions" {
  description = "Lambda functions created for the pipeline"
  value       = module.entity_resolution_pipeline.lambda_functions
}

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.entity_resolution_pipeline.state_machine_arn
}

output "schema_name" {
  description = "Entity Resolution schema name"
  value       = module.entity_resolution_pipeline.schema_name
}

output "workflow_name" {
  description = "Entity Resolution workflow name"
  value       = module.entity_resolution_pipeline.workflow_name
}
