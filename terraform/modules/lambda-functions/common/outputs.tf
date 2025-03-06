output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda IAM role"
  value       = aws_iam_role.lambda_role.name
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.lambda.arn
}
