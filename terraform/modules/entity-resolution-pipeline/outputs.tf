output "s3_bucket" {
  description = "The S3 bucket created for data storage"
  value = {
    id     = module.storage.bucket_id
    arn    = module.storage.bucket_arn
    region = var.aws_region
  }
}

output "lambda_functions" {
  description = "Lambda functions created for the pipeline"
  value = {
    load_data = {
      name = module.lambda_functions.load_data.function_name
      arn  = module.lambda_functions.load_data.arn
    }
    check_status = {
      name = module.lambda_functions.check_status.function_name
      arn  = module.lambda_functions.check_status.arn
    }
    process_data = {
      name = module.lambda_functions.process_data.function_name
      arn  = module.lambda_functions.process_data.arn
    }
    notify = {
      name = module.lambda_functions.notify.function_name
      arn  = module.lambda_functions.notify.arn
    }
  }
}

output "function_names" {
  description = "Map of function names for reference"
  value       = module.lambda_functions.function_names
}

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.step_functions.state_machine_arn
}

output "schema_name" {
  description = "Entity Resolution schema name"
  value       = module.schema.schema_name
}

output "workflow_name" {
  description = "Entity Resolution workflow name"
  value       = var.er_workflow_name
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encryption"
  value       = module.security.kms_key_arn
}

output "security_group_id" {
  description = "ID of the security group for Lambda functions"
  value       = module.security.lambda_security_group_id
}

output "event_trigger_lambda" {
  description = "Event trigger Lambda details"
  value       = var.enable_event_trigger ? module.event_trigger[0].lambda_function : null
}

output "event_trigger_rule" {
  description = "EventBridge rule details if S3 trigger is enabled"
  value       = var.enable_event_trigger ? module.event_trigger[0].event_rule : null
}
