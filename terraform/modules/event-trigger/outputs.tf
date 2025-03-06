output "lambda_function" {
  description = "Details of the event trigger Lambda function"
  value = var.enabled ? {
    function_name = aws_lambda_function.event_trigger[0].function_name
    arn           = aws_lambda_function.event_trigger[0].arn
    role_arn      = aws_iam_role.event_trigger[0].arn
    invoke_arn    = aws_lambda_function.event_trigger[0].invoke_arn
  } : null
}

output "event_rule" {
  description = "EventBridge rule details if S3 trigger is enabled"
  value = var.enabled && var.enable_s3_trigger ? {
    name = aws_cloudwatch_event_rule.s3_event[0].name
    arn  = aws_cloudwatch_event_rule.s3_event[0].arn
  } : null
}

output "is_enabled" {
  description = "Whether the event trigger is enabled"
  value       = var.enabled
}
