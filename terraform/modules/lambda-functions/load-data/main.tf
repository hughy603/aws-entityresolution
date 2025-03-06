locals {
  function_name = "load-data"
}

module "lambda_common" {
  source = "../common"

  project_name       = var.project_name
  function_name      = local.function_name
  environment        = var.environment
  tags               = var.tags
  vpc_config         = var.vpc_config
  enable_xray        = var.enable_xray
  kms_key_arn        = var.kms_key_arn
  s3_bucket          = var.s3_bucket
  log_retention_days = var.log_retention_days
}

# Lambda Function
resource "aws_lambda_function" "load_data" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "${var.project_name}-${local.function_name}"
  role          = module.lambda_common.lambda_role_arn
  handler       = "handler.lambda_handler"
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  layers        = [var.lambda_layer_arn]

  environment {
    variables = {
      AWS_REGION           = var.aws_region
      S3_BUCKET_NAME       = var.s3_bucket.name
      S3_INPUT_PREFIX      = var.s3_bucket.input_prefix
      S3_OUTPUT_PREFIX     = var.s3_bucket.output_prefix
      ER_WORKFLOW_NAME     = var.entity_resolution_config.workflow_name
      ER_SCHEMA_NAME       = var.entity_resolution_config.schema_name
      ER_ENTITY_ATTRIBUTES = join(",", var.entity_resolution_config.entity_attributes)
    }
  }

  dynamic "vpc_config" {
    for_each = length(var.vpc_config.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_config.subnet_ids
      security_group_ids = var.vpc_config.security_group_ids
    }
  }

  tags = var.tags
}

# Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/dist/${local.function_name}.zip"
}
