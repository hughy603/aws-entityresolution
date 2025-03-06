locals {
  function_name = "${var.project_name}-${var.environment}-event-trigger"
}

# IAM role for the event trigger Lambda
resource "aws_iam_role" "event_trigger" {
  count = var.enabled ? 1 : 0
  name  = "${local.function_name}-role"

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

  tags = var.tags
}

# IAM policy to allow the Lambda to start Step Functions executions
resource "aws_iam_policy" "step_functions_start" {
  count       = var.enabled ? 1 : 0
  name        = "${local.function_name}-sfn-policy"
  description = "Allow Lambda to start Step Functions executions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "states:StartExecution"
        Effect   = "Allow"
        Resource = var.step_function_arn
      }
    ]
  })
}

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "step_functions_start" {
  count      = var.enabled ? 1 : 0
  role       = aws_iam_role.event_trigger[0].name
  policy_arn = aws_iam_policy.step_functions_start[0].arn
}

# Basic Lambda logging policy
resource "aws_iam_policy" "lambda_logging" {
  count       = var.enabled ? 1 : 0
  name        = "${local.function_name}-logging-policy"
  description = "Allow Lambda to write logs to CloudWatch"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach logging policy to the role
resource "aws_iam_role_policy_attachment" "lambda_logging" {
  count      = var.enabled ? 1 : 0
  role       = aws_iam_role.event_trigger[0].name
  policy_arn = aws_iam_policy.lambda_logging[0].arn
}

# Lambda function for event triggering
resource "aws_lambda_function" "event_trigger" {
  count         = var.enabled ? 1 : 0
  function_name = local.function_name
  description   = "Triggers Entity Resolution Step Functions workflow based on events"
  role          = aws_iam_role.event_trigger[0].arn
  handler       = "index.handler"
  runtime       = var.runtime
  memory_size   = var.memory_size
  timeout       = var.timeout

  # Use inline code for a simple function
  filename         = data.archive_file.lambda_zip[0].output_path
  source_code_hash = data.archive_file.lambda_zip[0].output_base64sha256

  environment {
    variables = {
      STATE_MACHINE_ARN = var.step_function_arn
      ENVIRONMENT       = var.environment
      PROJECT_NAME      = var.project_name
    }
  }

  # VPC configuration if provided
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  tags = var.tags
}

# Create a simple Lambda deployment package with the event trigger code
data "archive_file" "lambda_zip" {
  count       = var.enabled ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"

  source {
    content  = <<-EOF
    exports.handler = async (event, context) => {
      console.log('Event received:', JSON.stringify(event, null, 2));

      const AWS = require('aws-sdk');
      const stepFunctions = new AWS.StepFunctions();

      const stateMachineArn = process.env.STATE_MACHINE_ARN;

      try {
        // Extract relevant information from the event
        const executionInput = {
          event: event,
          timestamp: new Date().toISOString(),
          source: event.source || 'event-trigger'
        };

        // Start Step Functions execution
        const params = {
          stateMachineArn: stateMachineArn,
          name: `event-trigger-$${Date.now()}`,
          input: JSON.stringify(executionInput)
        };

        const result = await stepFunctions.startExecution(params).promise();
        console.log('Step Functions execution started:', result);

        return {
          statusCode: 200,
          body: JSON.stringify({
            message: 'Step Functions execution started successfully',
            executionArn: result.executionArn
          })
        };
      } catch (error) {
        console.error('Error starting Step Functions execution:', error);
        throw error;
      }
    };
    EOF
    filename = "index.js"
  }
}

# CloudWatch Log Group for the Lambda function
resource "aws_cloudwatch_log_group" "event_trigger" {
  count             = var.enabled ? 1 : 0
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# Optional EventBridge Rule for S3 events
resource "aws_cloudwatch_event_rule" "s3_event" {
  count       = var.enabled && var.enable_s3_trigger ? 1 : 0
  name        = "${local.function_name}-s3-rule"
  description = "Capture S3 events and trigger Entity Resolution pipeline"
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.trigger_bucket_name]
      }
      object = {
        key = [{
          prefix = var.trigger_prefix
        }]
      }
    }
  })

  tags = var.tags
}

# Connect EventBridge Rule to Lambda
resource "aws_cloudwatch_event_target" "s3_event_target" {
  count     = var.enabled && var.enable_s3_trigger ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_event[0].name
  target_id = "TriggerLambda"
  arn       = aws_lambda_function.event_trigger[0].arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.enabled && var.enable_s3_trigger ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_trigger[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_event[0].arn
}
