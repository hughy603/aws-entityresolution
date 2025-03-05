# CloudWatch Alarms for Entity Resolution Pipeline

# Alarm for Step Functions Execution Failures
resource "aws_cloudwatch_metric_alarm" "step_functions_failures" {
  alarm_name          = "${var.project_name}-step-functions-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 0 # Any failure is an issue
  alarm_description   = "Alerts when Entity Resolution Pipeline executions fail"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.entity_resolution_pipeline.arn
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# Alarm for Step Functions Executions That Take Too Long
resource "aws_cloudwatch_metric_alarm" "step_functions_long_executions" {
  alarm_name          = "${var.project_name}-step-functions-long-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = 86400 # 24 hours
  statistic           = "Maximum"
  threshold           = 10800 # Alert if any execution takes more than 3 hours
  alarm_description   = "Alerts when Entity Resolution Pipeline executions take longer than expected"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.entity_resolution_pipeline.arn
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# Alarm for Entity Resolution Matching Job Failures
resource "aws_cloudwatch_metric_alarm" "entity_resolution_job_failures" {
  alarm_name          = "${var.project_name}-entity-resolution-job-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "JobsFailed"
  namespace           = "Custom/EntityResolution"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 0 # Any failure is an issue
  alarm_description   = "Alerts when Entity Resolution matching jobs fail"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
  tags = var.default_tags
}

# SNS Topic Subscription for Email Notifications
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Dashboard for Entity Resolution Pipeline
resource "aws_cloudwatch_dashboard" "entity_resolution" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.entity_resolution_pipeline.arn],
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.entity_resolution_pipeline.arn],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.entity_resolution_pipeline.arn]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Step Functions Executions"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.entity_resolution_pipeline.arn, { "stat" : "Average" }],
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.entity_resolution_pipeline.arn, { "stat" : "Maximum" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Step Functions Execution Duration"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          query  = "SOURCE '/aws/lambda/${aws_lambda_function.process.function_name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region = var.aws_region
          title  = "Entity Resolution Process Lambda Logs"
          view   = "table"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          query  = "SOURCE '/aws/lambda/${aws_lambda_function.check_status.function_name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region = var.aws_region
          title  = "Entity Resolution Check Status Lambda Logs"
          view   = "table"
        }
      }
    ]
  })
}
