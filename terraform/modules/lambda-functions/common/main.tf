locals {
  lambda_base_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "lambda"
    }
  )
}

# Common IAM role for Lambda functions
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.function_name}-role"

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

  tags = local.lambda_base_tags
}

# Common Lambda CloudWatch Logs policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access policy (if VPC config is provided)
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  count      = length(var.vpc_config.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# X-Ray tracing policy (if enabled)
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  count      = var.enable_xray ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Common CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.function_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = local.lambda_base_tags
}

# S3 access policy
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-${var.function_name}-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket.name}",
          "arn:aws:s3:::${var.s3_bucket.name}/*"
        ]
      }
    ]
  })
}
