# Lambda Function for Notifications
resource "aws_lambda_function" "notify" {
  filename      = data.archive_file.notify_lambda.output_path
  function_name = "${var.project_name}-notify"
  role          = aws_iam_role.notify_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512
  layers        = [aws_lambda_layer_version.entity_resolution_layer.arn]

  environment {
    variables = {
      AWS_REGION                      = var.aws_region
      SNS_TOPIC_ARN                   = aws_sns_topic.entity_resolution_notifications.arn
      ENTITY_RESOLUTION_DASHBOARD_URL = var.entity_resolution_dashboard_url
    }
  }

  tags = var.default_tags
}

# Lambda IAM Role
resource "aws_iam_role" "notify_lambda" {
  name = "${var.project_name}-notify-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.default_tags
}

# Lambda IAM Policy
resource "aws_iam_role_policy" "notify_lambda" {
  name = "${var.project_name}-notify-lambda-policy"
  role = aws_iam_role.notify_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [aws_sns_topic.pipeline_notifications.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      }
    ]
  })
}

# Lambda CloudWatch Log Group
resource "aws_cloudwatch_log_group" "notify_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.notify.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

# Lambda Code Archive
data "archive_file" "notify_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/notify"
  output_path = "${path.module}/lambda/notify.zip"
}

# SNS Topic for Pipeline Notifications
resource "aws_sns_topic" "pipeline_notifications" {
  name = "${var.project_name}-notifications"
  tags = var.default_tags
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "pipeline_notifications" {
  arn = aws_sns_topic.pipeline_notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.pipeline_notifications.arn
      }
    ]
  })
}

# SNS Topic Subscription
resource "aws_sns_topic_subscription" "pipeline_notifications_email" {
  count     = length(var.notification_emails)
  topic_arn = aws_sns_topic.pipeline_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}
