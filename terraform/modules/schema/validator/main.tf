locals {
  schema_content = var.schema_file != null ? file(var.schema_file) : "{}"
}

# Lambda function for schema validation
resource "aws_lambda_function" "schema_validator" {
  filename      = "${path.module}/lambda/schema_validator.zip"
  function_name = "${var.config.project_name}-${var.config.environment}-schema-validator"
  role          = aws_iam_role.validator_role.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      SCHEMA_CONTENT    = local.schema_content
      ENTITY_ATTRIBUTES = jsonencode(var.entity_attributes)
    }
  }

  tags = var.config.tags
}

# IAM role for the validator Lambda
resource "aws_iam_role" "validator_role" {
  name = "${var.config.project_name}-${var.config.environment}-validator-role"

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

  tags = var.config.tags
}

# CloudWatch Logs policy for the validator Lambda
resource "aws_iam_role_policy_attachment" "validator_logs" {
  role       = aws_iam_role.validator_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
