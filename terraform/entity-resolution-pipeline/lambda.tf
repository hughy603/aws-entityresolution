# Lambda functions for Entity Resolution Pipeline
# Uses a single codebase with multiple handlers for different pipeline steps

# ZIP the Lambda code
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_package"
  output_path = "${path.module}/build/lambda_package.zip"
}

# Lambda Layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-dependencies"
  description         = "Dependencies for Entity Resolution Pipeline"
  filename            = "${path.module}/build/lambda_layer.zip"
  compatible_runtimes = ["python3.12"]

  # Assume the layer ZIP is created outside Terraform or by a null_resource
  # in a production environment

  lifecycle {
    create_before_destroy = true
  }
}

# Lambda execution role
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.default_tags
}

# Attach policies to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# Custom policy for Lambda to access Entity Resolution, Secrets, and other services
resource "aws_iam_policy" "lambda_entity_resolution" {
  name        = "${var.project_name}-lambda-er-policy"
  description = "Policy for Lambda to access Entity Resolution and other services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "entityresolution:*",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_entity_resolution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_entity_resolution.arn
}

# Define Lambda functions with different handlers from the same codebase
resource "aws_lambda_function" "lambda_handlers" {
  for_each = {
    extract = {
      handler     = "aws_entity_resolution.lambda_handlers.extract_handler"
      description = "Extract entity data from Snowflake to S3"
      memory      = 256
      timeout     = 120
      env_vars    = merge(local.common_env_vars, local.extract_env_vars)
    }
    process = {
      handler     = "aws_entity_resolution.lambda_handlers.process_handler"
      description = "Process data through AWS Entity Resolution"
      memory      = 256
      timeout     = 60
      env_vars    = merge(local.common_env_vars, local.process_env_vars)
    }
    check_status = {
      handler     = "aws_entity_resolution.lambda_handlers.check_status_handler"
      description = "Check status of Entity Resolution job"
      memory      = 128
      timeout     = 30
      env_vars    = merge(local.common_env_vars, local.process_env_vars)
    }
    load = {
      handler     = "aws_entity_resolution.lambda_handlers.load_handler"
      description = "Load matched records from S3 to Snowflake"
      memory      = 256
      timeout     = 120
      env_vars    = merge(local.common_env_vars, local.load_env_vars)
    }
  }

  function_name = "${var.project_name}-${each.key}"
  description   = each.value.description
  role          = aws_iam_role.lambda_exec.arn

  # Use a single package for all functions with different handlers
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  handler          = each.value.handler

  runtime     = "python3.12"
  memory_size = each.value.memory
  timeout     = each.value.timeout

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = each.value.env_vars
  }

  # CloudWatch log group with retention
  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group
  ]

  tags = var.default_tags
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  for_each = {
    extract      = "/aws/lambda/${var.project_name}-extract"
    process      = "/aws/lambda/${var.project_name}-process"
    check_status = "/aws/lambda/${var.project_name}-check_status"
    load         = "/aws/lambda/${var.project_name}-load"
  }

  name              = each.value
  retention_in_days = 30

  tags = var.default_tags
}

# Local variables for environment variables
locals {
  common_env_vars = {
    AWS_REGION     = var.aws_region
    S3_BUCKET_NAME = var.s3_bucket_name
    LOG_LEVEL      = "INFO"
    SCHEMA_NAME    = var.schema_name
  }

  extract_env_vars = {
    S3_PREFIX                 = var.s3_input_prefix
    SNOWFLAKE_ACCOUNT         = var.snowflake_account
    SNOWFLAKE_USERNAME        = var.snowflake_username
    SNOWFLAKE_PASSWORD        = var.snowflake_password
    SNOWFLAKE_ROLE            = var.snowflake_role
    SNOWFLAKE_WAREHOUSE       = var.snowflake_warehouse
    SNOWFLAKE_SOURCE_DATABASE = var.snowflake_source_database
    SNOWFLAKE_SOURCE_SCHEMA   = var.snowflake_source_schema
    SNOWFLAKE_SOURCE_TABLE    = var.source_table
  }

  process_env_vars = {
    ER_WORKFLOW_NAME = var.matching_workflow_name
  }

  load_env_vars = {
    S3_PREFIX                 = var.s3_output_prefix
    SNOWFLAKE_ACCOUNT         = var.snowflake_account
    SNOWFLAKE_USERNAME        = var.snowflake_username
    SNOWFLAKE_PASSWORD        = var.snowflake_password
    SNOWFLAKE_ROLE            = var.snowflake_role
    SNOWFLAKE_WAREHOUSE       = var.snowflake_warehouse
    SNOWFLAKE_TARGET_DATABASE = var.snowflake_target_database
    SNOWFLAKE_TARGET_SCHEMA   = var.snowflake_target_schema
    SNOWFLAKE_TARGET_TABLE    = var.target_table
  }
}
