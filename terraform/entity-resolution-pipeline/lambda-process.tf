# Lambda Function for Process Step
resource "aws_lambda_function" "process" {
  filename      = data.archive_file.process_lambda.output_path
  function_name = "${var.project_name}-process"
  role          = aws_iam_role.process_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512
  layers        = [aws_lambda_layer_version.entity_resolution_layer.arn]

  environment {
    variables = {
      AWS_REGION           = var.aws_region
      S3_BUCKET_NAME       = var.s3_bucket_name
      S3_PREFIX            = var.s3_input_prefix
      S3_OUTPUT_PREFIX     = var.s3_output_prefix
      ER_WORKFLOW_NAME     = var.er_workflow_name
      ER_SCHEMA_NAME       = var.er_schema_name
      ER_ENTITY_ATTRIBUTES = join(",", var.er_entity_attributes)
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = var.default_tags
}

# Lambda IAM Role
resource "aws_iam_role" "process_lambda" {
  name = "${var.project_name}-process-lambda-role"

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
resource "aws_iam_role_policy" "process_lambda" {
  name = "${var.project_name}-process-lambda-policy"
  role = aws_iam_role.process_lambda.id

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
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "entityresolution:StartMatchingJob",
          "entityresolution:GetMatchingJob",
          "entityresolution:ListMatchingJobs"
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# Lambda CloudWatch Log Group
resource "aws_cloudwatch_log_group" "process_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.process.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

# Lambda Code Archive
data "archive_file" "process_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/process"
  output_path = "${path.module}/lambda/process.zip"
}
