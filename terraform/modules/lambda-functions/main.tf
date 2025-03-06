locals {
  lambda_functions = {
    load = {
      name        = "load"
      handler     = "handler.lambda_handler"
      description = "Loads data for Entity Resolution processing"
    }
    process = {
      name        = "process"
      handler     = "handler.lambda_handler"
      description = "Processes data through Entity Resolution"
    }
    check_status = {
      name        = "check-status"
      handler     = "handler.lambda_handler"
      description = "Checks Entity Resolution job status"
    }
    notify = {
      name        = "notify"
      handler     = "handler.lambda_handler"
      description = "Sends notifications about Entity Resolution results"
    }
  }

  common_lambda_config = {
    runtime     = "python3.11"
    memory_size = var.lambda_memory_size
    timeout     = var.lambda_timeout
    layers      = [var.lambda_layer_arn]
  }

  common_environment_variables = {
    AWS_REGION           = var.aws_region
    S3_BUCKET_NAME       = var.s3_bucket_name
    S3_INPUT_PREFIX      = var.s3_input_prefix
    S3_OUTPUT_PREFIX     = var.s3_output_prefix
    ER_WORKFLOW_NAME     = var.er_workflow_name
    ER_SCHEMA_NAME       = var.er_schema_name
    ER_ENTITY_ATTRIBUTES = join(",", var.er_entity_attributes)
  }
}

# Lambda Functions
resource "aws_lambda_function" "load" {
  filename      = data.archive_file.load_lambda.output_path
  function_name = "${var.project_name}-${local.lambda_functions.load.name}"
  role          = aws_iam_role.load_lambda.arn
  handler       = local.lambda_functions.load.handler
  description   = local.lambda_functions.load.description

  runtime     = local.common_lambda_config.runtime
  memory_size = local.common_lambda_config.memory_size
  timeout     = local.common_lambda_config.timeout
  layers      = local.common_lambda_config.layers

  environment {
    variables = local.common_environment_variables
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [aws_security_group.lambda[0].id]
    }
  }

  tags = var.default_tags
}

# Process Lambda Function
resource "aws_lambda_function" "process" {
  filename      = data.archive_file.process_lambda.output_path
  function_name = "${var.project_name}-${local.lambda_functions.process.name}"
  role          = aws_iam_role.process_lambda.arn
  handler       = local.lambda_functions.process.handler
  description   = local.lambda_functions.process.description

  runtime     = local.common_lambda_config.runtime
  memory_size = local.common_lambda_config.memory_size
  timeout     = local.common_lambda_config.timeout
  layers      = local.common_lambda_config.layers

  environment {
    variables = local.common_environment_variables
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [aws_security_group.lambda[0].id]
    }
  }

  tags = var.default_tags
}

# Check Status Lambda Function
resource "aws_lambda_function" "check_status" {
  filename      = data.archive_file.check_status_lambda.output_path
  function_name = "${var.project_name}-${local.lambda_functions.check_status.name}"
  role          = aws_iam_role.check_status_lambda.arn
  handler       = local.lambda_functions.check_status.handler
  description   = local.lambda_functions.check_status.description

  runtime     = local.common_lambda_config.runtime
  memory_size = local.common_lambda_config.memory_size
  timeout     = local.common_lambda_config.timeout
  layers      = local.common_lambda_config.layers

  environment {
    variables = local.common_environment_variables
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [aws_security_group.lambda[0].id]
    }
  }

  tags = var.default_tags
}

# Notify Lambda Function
resource "aws_lambda_function" "notify" {
  filename      = data.archive_file.notify_lambda.output_path
  function_name = "${var.project_name}-${local.lambda_functions.notify.name}"
  role          = aws_iam_role.notify_lambda.arn
  handler       = local.lambda_functions.notify.handler
  description   = local.lambda_functions.notify.description

  runtime     = local.common_lambda_config.runtime
  memory_size = local.common_lambda_config.memory_size
  timeout     = local.common_lambda_config.timeout
  layers      = local.common_lambda_config.layers

  environment {
    variables = local.common_environment_variables
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [aws_security_group.lambda[0].id]
    }
  }

  tags = var.default_tags
}

# IAM Roles and Policies
resource "aws_iam_role" "load_lambda" {
  name = "${var.project_name}-${local.lambda_functions.load.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.default_tags
}

resource "aws_iam_role_policy" "load_lambda" {
  name = "${var.project_name}-${local.lambda_functions.load.name}-policy"
  role = aws_iam_role.load_lambda.id

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
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      }
    ]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "load_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.load.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

# VPC Security Group (if VPC config is enabled)
resource "aws_security_group" "lambda" {
  count  = length(var.subnet_ids) > 0 ? 1 : 0
  name   = "${var.project_name}-lambda-sg"
  vpc_id = data.aws_subnet.first[0].vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.default_tags
}

# Data source to get VPC ID from subnet (if VPC config is enabled)
data "aws_subnet" "first" {
  count = length(var.subnet_ids) > 0 ? 1 : 0
  id    = var.subnet_ids[0]
}

# Lambda deployment packages
data "archive_file" "load_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/functions/load"
  output_path = "${path.module}/functions/load.zip"
}

# IAM Roles and Policies for remaining functions
resource "aws_iam_role" "process_lambda" {
  name = "${var.project_name}-${local.lambda_functions.process.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.default_tags
}

resource "aws_iam_role" "check_status_lambda" {
  name = "${var.project_name}-${local.lambda_functions.check_status.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.default_tags
}

resource "aws_iam_role" "notify_lambda" {
  name = "${var.project_name}-${local.lambda_functions.notify.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.default_tags
}

# CloudWatch Log Groups for remaining functions
resource "aws_cloudwatch_log_group" "process_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.process.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

resource "aws_cloudwatch_log_group" "check_status_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.check_status.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

resource "aws_cloudwatch_log_group" "notify_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.notify.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

# Lambda deployment packages for remaining functions
data "archive_file" "process_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/functions/process"
  output_path = "${path.module}/functions/process.zip"
}

data "archive_file" "check_status_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/functions/check_status"
  output_path = "${path.module}/functions/check_status.zip"
}

data "archive_file" "notify_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/functions/notify"
  output_path = "${path.module}/functions/notify.zip"
}

# IAM Policies for remaining functions
resource "aws_iam_role_policy" "process_lambda" {
  name = "${var.project_name}-${local.lambda_functions.process.name}-policy"
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
      }
    ]
  })
}

resource "aws_iam_role_policy" "check_status_lambda" {
  name = "${var.project_name}-${local.lambda_functions.check_status.name}-policy"
  role = aws_iam_role.check_status_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
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
      }
    ]
  })
}

resource "aws_iam_role_policy" "notify_lambda" {
  name = "${var.project_name}-${local.lambda_functions.notify.name}-policy"
  role = aws_iam_role.notify_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
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
          "sns:Publish"
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
      }
    ]
  })
}

module "check_status" {
  source = "./check-status"

  project_name             = var.project_name
  aws_region               = var.aws_region
  environment              = var.environment
  lambda_runtime           = var.lambda_runtime
  lambda_timeout           = var.lambda_timeout
  lambda_memory_size       = var.lambda_memory_size
  vpc_config               = var.vpc_config
  tags                     = var.tags
  lambda_layer_arn         = var.lambda_layer_arn
  s3_bucket                = var.s3_bucket
  entity_resolution_config = var.entity_resolution_config
  kms_key_arn              = var.kms_key_arn
  enable_xray              = var.enable_xray
  log_retention_days       = var.log_retention_days
}

module "load_data" {
  source = "./load-data"

  project_name             = var.project_name
  aws_region               = var.aws_region
  environment              = var.environment
  lambda_runtime           = var.lambda_runtime
  lambda_timeout           = var.lambda_timeout
  lambda_memory_size       = var.lambda_memory_size
  vpc_config               = var.vpc_config
  tags                     = var.tags
  lambda_layer_arn         = var.lambda_layer_arn
  s3_bucket                = var.s3_bucket
  entity_resolution_config = var.entity_resolution_config
  kms_key_arn              = var.kms_key_arn
  enable_xray              = var.enable_xray
  log_retention_days       = var.log_retention_days
}

module "process_data" {
  source = "./process-data"

  project_name             = var.project_name
  aws_region               = var.aws_region
  environment              = var.environment
  lambda_runtime           = var.lambda_runtime
  lambda_timeout           = var.lambda_timeout
  lambda_memory_size       = var.lambda_memory_size
  vpc_config               = var.vpc_config
  tags                     = var.tags
  lambda_layer_arn         = var.lambda_layer_arn
  s3_bucket                = var.s3_bucket
  entity_resolution_config = var.entity_resolution_config
  kms_key_arn              = var.kms_key_arn
  enable_xray              = var.enable_xray
  log_retention_days       = var.log_retention_days
}

module "notify" {
  source = "./notify"

  project_name             = var.project_name
  aws_region               = var.aws_region
  environment              = var.environment
  lambda_runtime           = var.lambda_runtime
  lambda_timeout           = var.lambda_timeout
  lambda_memory_size       = var.lambda_memory_size
  vpc_config               = var.vpc_config
  tags                     = var.tags
  lambda_layer_arn         = var.lambda_layer_arn
  s3_bucket                = var.s3_bucket
  entity_resolution_config = var.entity_resolution_config
  kms_key_arn              = var.kms_key_arn
  enable_xray              = var.enable_xray
  log_retention_days       = var.log_retention_days
}
