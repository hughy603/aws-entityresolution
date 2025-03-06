output "lambda_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.load_data.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.load_data.function_name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = module.lambda_common.lambda_role_arn
}

output "security_group_id" {
  description = "ID of the Lambda security group (if VPC config is enabled)"
  value       = length(var.subnet_ids) > 0 ? aws_security_group.lambda[0].id : null
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch Log Group"
  value       = module.lambda_common.cloudwatch_log_group_name
}
