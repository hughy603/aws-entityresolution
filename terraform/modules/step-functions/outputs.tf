output "state_machine_name" {
  description = "The name of the Step Functions state machine"
  value       = aws_sfn_state_machine.entity_resolution_workflow.name
}

output "state_machine_arn" {
  description = "The ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.entity_resolution_workflow.arn
}

output "execution_role_arn" {
  description = "The ARN of the IAM role used by the Step Functions state machine"
  value       = aws_iam_role.step_functions_role.arn
}

output "execution_role_name" {
  description = "The name of the IAM role used by the Step Functions state machine"
  value       = aws_iam_role.step_functions_role.name
}

output "role_arn" {
  description = "ARN of the Step Functions IAM role"
  value       = aws_iam_role.step_functions.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.step_functions.name
}

output "error_notification_topic" {
  description = "ARN of the SNS topic for error notifications (if enabled)"
  value       = try(local.error_notification.topic_arn, null)
}

output "iam_role" {
  description = "IAM role used by the Step Functions state machine"
  value = {
    name = aws_iam_role.step_functions.name
    arn  = aws_iam_role.step_functions.arn
  }
}

output "log_group" {
  description = "CloudWatch Log Group for Step Functions execution logs"
  value = {
    name = aws_cloudwatch_log_group.step_functions.name
    arn  = aws_cloudwatch_log_group.step_functions.arn
  }
}
