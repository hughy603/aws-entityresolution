locals {
  workflow_name = "${var.project_name}-entity-resolution-workflow"

  # Provide fallbacks for backward compatibility
  load_data_lambda_arn = var.lambda_functions != null && contains(keys(var.lambda_functions), "load_data") ? var.lambda_functions.load_data.arn : var.load_data_lambda_arn

  check_status_lambda_arn = var.lambda_functions != null && contains(keys(var.lambda_functions), "check_status") ? var.lambda_functions.check_status.arn : var.check_status_lambda_arn

  process_output_lambda_arn = var.lambda_functions != null && contains(keys(var.lambda_functions), "process_data") ? var.lambda_functions.process_data.arn : var.process_output_lambda_arn

  notify_lambda_arn = var.lambda_functions != null && contains(keys(var.lambda_functions), "notify") ? var.lambda_functions.notify.arn : var.notify_lambda_arn

  error_notification = var.error_notification_config.enabled ? {
    topic_arn = coalesce(
      var.error_notification_config.sns_topic_arn,
      aws_sns_topic.error_notifications[0].arn
    )
  } : null

  workflow_config = merge({
    max_concurrent_executions = 1
    execution_timeout_minutes = 60
    retry_attempts            = 3
    retry_interval_seconds    = 60
  }, var.workflow_config)
}

# SNS Topic for error notifications if enabled
resource "aws_sns_topic" "error_notifications" {
  count = var.error_notification_config.enabled && var.error_notification_config.sns_topic_arn == null ? 1 : 0

  name = "${local.workflow_name}-error-notifications"
  tags = var.default_tags
}

# SNS Topic subscription for email notifications
resource "aws_sns_topic_subscription" "error_email" {
  count = var.error_notification_config.enabled && var.error_notification_config.email != null ? 1 : 0

  topic_arn = local.error_notification.topic_arn
  protocol  = "email"
  endpoint  = var.error_notification_config.email
}

# IAM role for Step Functions state machine
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.default_tags
}

# IAM policy for Step Functions to invoke Lambda functions
resource "aws_iam_policy" "step_functions_policy" {
  name = "${var.project_name}-step-functions-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction"
        ]
        Effect = "Allow"
        Resource = [
          local.load_data_lambda_arn,
          local.check_status_lambda_arn,
          local.process_output_lambda_arn,
          local.notify_lambda_arn
        ]
      },
      {
        Action = [
          "logs:CreateLogDelivery",
          "logs:CreateLogStream",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutLogEvents",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# IAM policy for Step Functions to publish error notifications
resource "aws_iam_role_policy" "step_functions_sns" {
  count = var.error_notification_config.enabled ? 1 : 0

  name = "sns-publish"
  role = aws_iam_role.step_functions_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sns:Publish"
      ]
      Resource = [local.error_notification.topic_arn]
    }]
  })
}

# Step Functions state machine
resource "aws_sfn_state_machine" "entity_resolution_workflow" {
  name     = local.workflow_name
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/templates/workflow.json.tpl", {
    aws_region              = var.aws_region
    load_data_lambda_arn    = local.load_data_lambda_arn
    check_status_lambda_arn = local.check_status_lambda_arn
    process_data_lambda_arn = local.process_output_lambda_arn
    notify_lambda_arn       = local.notify_lambda_arn
    error_notification      = var.error_notification_config
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = var.default_tags
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${local.workflow_name}"
  retention_in_days = 30
  tags              = var.default_tags
}
resource "aws_iam_role_policy_attachment" "step_functions_policy_attachment" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.step_functions_policy.arn
}
