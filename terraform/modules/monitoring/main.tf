locals {
  dashboard_name = "${var.project_name}-entity-resolution-dashboard"

  # Create a dashboard with metrics for all Lambda functions
  lambda_widgets = [
    for idx, fn_key in keys(var.lambda_functions) : {
      type   = "metric"
      x      = (idx % 2) * 12
      y      = floor(idx / 2) * 6
      width  = 12
      height = 6
      properties = {
        title  = "${title(replace(fn_key, "_", " "))} Lambda Function"
        region = var.aws_region
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_functions[fn_key].function_name, { "stat" : "Sum" }],
          ["AWS/Lambda", "Errors", "FunctionName", var.lambda_functions[fn_key].function_name, { "stat" : "Sum" }],
          ["AWS/Lambda", "Duration", "FunctionName", var.lambda_functions[fn_key].function_name, { "stat" : "Average" }],
          ["AWS/Lambda", "Throttles", "FunctionName", var.lambda_functions[fn_key].function_name, { "stat" : "Sum" }]
        ]
        view    = "timeSeries"
        stacked = false
        period  = 300
      }
    }
  ]

  # Step Functions metrics
  step_function_widget = {
    type   = "metric"
    x      = 0
    y      = length(var.lambda_functions) * 3
    width  = 24
    height = 6
    properties = {
      title  = "Step Function Execution Metrics"
      region = var.aws_region
      metrics = [
        ["AWS/States", "ExecutionsStarted", { "stat" : "Sum" }],
        ["AWS/States", "ExecutionsSucceeded", { "stat" : "Sum" }],
        ["AWS/States", "ExecutionsFailed", { "stat" : "Sum" }],
        ["AWS/States", "ExecutionsTimedOut", { "stat" : "Sum" }]
      ]
      view    = "timeSeries"
      stacked = false
      period  = 300
    }
  }

  alarm_actions = var.alert_email != null ? [aws_sns_topic.alarms[0].arn] : []

  # Create a map of CloudWatch alarms for all Lambda functions
  lambda_alarms = flatten([
    for fn_key, fn in var.lambda_functions : [
      {
        name                = "${var.project_name}-${fn_key}-errors"
        function_name       = fn.function_name
        metric_name         = "Errors"
        threshold           = 1
        period              = 60
        statistic           = "Sum"
        description         = "Alarm when ${fn_key} Lambda function has errors"
        comparison_operator = "GreaterThanOrEqualToThreshold"
        treat_missing_data  = "notBreaching"
      },
      {
        name                = "${var.project_name}-${fn_key}-duration"
        function_name       = fn.function_name
        metric_name         = "Duration"
        threshold           = fn_key == "process_data" ? 25000 : 10000 # Higher threshold for process_data
        period              = 60
        statistic           = "Maximum"
        description         = "Alarm when ${fn_key} Lambda function duration exceeds threshold"
        comparison_operator = "GreaterThanThreshold"
        treat_missing_data  = "notBreaching"
      }
    ]
  ])
}

# SNS Topic for alarms
resource "aws_sns_topic" "alarms" {
  count = var.alert_email != null ? 1 : 0

  name = "${var.project_name}-alarms"
  tags = var.default_tags
}

# Email subscription for alarm notifications
resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email != null ? 1 : 0

  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "entity_resolution" {
  dashboard_name = local.dashboard_name

  dashboard_body = jsonencode({
    widgets = concat(local.lambda_widgets, [local.step_function_widget])
  })
}

# CloudWatch alarms for Lambda functions
resource "aws_cloudwatch_metric_alarm" "lambda_alarms" {
  count = length(local.lambda_alarms)

  alarm_name          = local.lambda_alarms[count.index].name
  comparison_operator = local.lambda_alarms[count.index].comparison_operator
  evaluation_periods  = 1
  metric_name         = local.lambda_alarms[count.index].metric_name
  namespace           = "AWS/Lambda"
  period              = local.lambda_alarms[count.index].period
  statistic           = local.lambda_alarms[count.index].statistic
  threshold           = local.lambda_alarms[count.index].threshold
  alarm_description   = local.lambda_alarms[count.index].description
  treat_missing_data  = local.lambda_alarms[count.index].treat_missing_data

  dimensions = {
    FunctionName = local.lambda_alarms[count.index].function_name
  }

  alarm_actions = local.alarm_actions
  ok_actions    = local.alarm_actions

  tags = var.default_tags
}

# CloudWatch alarm for Step Functions execution failures
resource "aws_cloudwatch_metric_alarm" "step_function_failure" {
  alarm_name          = "${var.project_name}-step-function-failure"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alarm when Step Functions execution fails"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = var.step_function_arn
  }

  alarm_actions = local.alarm_actions
  ok_actions    = local.alarm_actions

  tags = var.default_tags
}
