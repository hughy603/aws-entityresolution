output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "metric_alarms" {
  description = "Map of CloudWatch metric alarms"
  value = {
    step_functions  = aws_cloudwatch_metric_alarm.step_functions_failures.arn
    lambda_errors   = { for k, v in aws_cloudwatch_metric_alarm.lambda_errors : k => v.arn }
    lambda_duration = { for k, v in aws_cloudwatch_metric_alarm.lambda_duration : k => v.arn }
  }
}

output "log_metric_filters" {
  description = "Map of CloudWatch log metric filters"
  value       = { for k, v in aws_cloudwatch_log_metric_filter.error_logs : k => v.name }
}
