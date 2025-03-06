output "step_functions_state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.step_functions.state_machine_arn
}

output "load_data_lambda_function_name" {
  description = "Name of the load data Lambda function"
  value       = module.load_data_lambda.lambda_function_name
}

output "check_status_lambda_function_name" {
  description = "Name of the check status Lambda function"
  value       = module.check_status_lambda.lambda_function_name
}

output "process_output_lambda_function_name" {
  description = "Name of the process output Lambda function"
  value       = module.process_output_lambda.lambda_function_name
}

output "notify_lambda_function_name" {
  description = "Name of the notification Lambda function"
  value       = module.notify_lambda.lambda_function_name
}

output "cloudwatch_log_group_names" {
  description = "Names of the CloudWatch log groups"
  value = {
    step_functions = module.step_functions.cloudwatch_log_group_name
    load_data      = module.load_data_lambda.cloudwatch_log_group_name
    check_status   = module.check_status_lambda.cloudwatch_log_group_name
    process_output = module.process_output_lambda.cloudwatch_log_group_name
    notify         = module.notify_lambda.cloudwatch_log_group_name
  }
}
