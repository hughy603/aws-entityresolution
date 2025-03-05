# Lambda Function for Load Step
resource "aws_lambda_function" "load" {
  filename      = data.archive_file.load_lambda.output_path
  function_name = "${var.project_name}-load"
  role          = aws_iam_role.load_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512
  layers        = [aws_lambda_layer_version.entity_resolution_layer.arn]

  environment {
    variables = {
      AWS_REGION                = var.aws_region
      S3_BUCKET_NAME            = var.s3_bucket_name
      S3_PREFIX                 = var.s3_input_prefix
      SNOWFLAKE_ACCOUNT         = var.snowflake_account
      SNOWFLAKE_USERNAME        = var.snowflake_username
      SNOWFLAKE_PASSWORD        = data.aws_secretsmanager_secret_version.snowflake_password.secret_string
      SNOWFLAKE_ROLE            = var.snowflake_role
      SNOWFLAKE_WAREHOUSE       = var.snowflake_warehouse
      SNOWFLAKE_TARGET_DATABASE = var.snowflake_target_database
      SNOWFLAKE_TARGET_SCHEMA   = var.snowflake_target_schema
      SNOWFLAKE_TARGET_TABLE    = var.snowflake_target_table
      ER_ENTITY_ATTRIBUTES      = join(",", var.er_entity_attributes)
    }
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = var.default_tags
}

# Lambda IAM Role
resource "aws_iam_role" "load_lambda" {
  name = "${var.project_name}-load-lambda-role"

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
resource "aws_iam_role_policy" "load_lambda" {
  name = "${var.project_name}-load-lambda-policy"
  role = aws_iam_role.load_lambda.id

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
          "secretsmanager:GetSecretValue"
        ]
        Resource = [data.aws_secretsmanager_secret.snowflake_password.arn]
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
resource "aws_cloudwatch_log_group" "load_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.load.function_name}"
  retention_in_days = 30
  tags              = var.default_tags
}

# Lambda Code Archive
data "archive_file" "load_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/load"
  output_path = "${path.module}/lambda/load.zip"
}

# Create Lambda Layer for aws_entity_resolution package
resource "aws_lambda_layer_version" "entity_resolution_layer" {
  layer_name = "${var.project_name}-entity-resolution-layer"

  filename         = "${path.module}/../layer/python.zip"
  source_code_hash = filebase64sha256("${path.module}/../layer/python.zip")

  compatible_runtimes = ["python3.11"]
}

# Create a build script to prepare the Lambda layer
resource "null_resource" "prepare_lambda_layer" {
  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = <<EOT
      mkdir -p ${path.module}/../layer/python
      cp ${path.module}/../../dist/aws_entity_resolution-*.whl ${path.module}/../layer/
      cd ${path.module}/../layer
      pip install aws_entity_resolution-*.whl -t python/
      zip -r python.zip python/
      rm -rf python/
      rm aws_entity_resolution-*.whl
    EOT
  }
}

# Ensure the Lambda function depends on the layer
resource "null_resource" "dependency_layer" {
  triggers = {
    layer_id = aws_lambda_layer_version.entity_resolution_layer.id
  }

  depends_on = [null_resource.prepare_lambda_layer]
}
