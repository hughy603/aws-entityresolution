terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.68"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-entity-resolution"
    key            = "entity-resolution-pipeline/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.default_tags
  }
}

provider "snowflake" {
  account  = var.snowflake_account
  username = var.snowflake_username
  password = var.snowflake_password
  role     = var.snowflake_role
}

# Create a new S3 bucket for entity resolution data
resource "aws_s3_bucket" "entity_resolution_data" {
  bucket = var.s3_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

# Configure S3 bucket properties
resource "aws_s3_bucket_versioning" "entity_resolution_data" {
  bucket = aws_s3_bucket.entity_resolution_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "entity_resolution_data" {
  bucket = aws_s3_bucket.entity_resolution_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "entity_resolution_data" {
  bucket = aws_s3_bucket.entity_resolution_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Create IAM role for AWS Glue
resource "aws_iam_role" "glue_role" {
  name = var.glue_iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# Attach policies to Glue role
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_policy" "glue_entity_resolution" {
  name        = "GlueEntityResolutionPolicy"
  description = "Policy for Glue to access Entity Resolution and Secrets Manager"

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
          "entityresolution:*"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_entity_resolution" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_entity_resolution.arn
}

# Create the Snowflake extractor module
module "snowflake_extractor" {
  source = "./modules/snowflake_extractor"

  snowflake_account   = var.snowflake_account
  snowflake_username  = var.snowflake_username
  snowflake_password  = var.snowflake_password
  snowflake_role      = var.snowflake_role
  snowflake_warehouse = var.snowflake_warehouse
  snowflake_database  = var.snowflake_source_database
  snowflake_schema    = var.snowflake_source_schema
  source_table        = var.source_table

  s3_bucket         = aws_s3_bucket.entity_resolution_data.bucket
  s3_prefix         = var.s3_input_prefix
  aws_region        = var.aws_region
  entity_attributes = var.entity_attributes

  extraction_glue_job_name = var.extraction_glue_job_name
  glue_iam_role            = aws_iam_role.glue_role.arn
  extraction_schedule      = var.extraction_schedule

  tags = var.resource_tags
}

# Create the Entity Resolution module
module "entity_resolution" {
  source = "./modules/entity_resolution"

  aws_region                  = var.aws_region
  entity_resolution_role_name = var.entity_resolution_role_name

  s3_bucket        = aws_s3_bucket.entity_resolution_data.bucket
  input_s3_prefix  = var.s3_input_prefix
  output_s3_prefix = var.s3_output_prefix

  matching_workflow_name = var.matching_workflow_name
  schema_name            = var.schema_name
  entity_attributes      = var.entity_attributes

  glue_job_name = var.entity_resolution_glue_job_name
  glue_iam_role = aws_iam_role.glue_role.arn

  tags = var.resource_tags

  # # depends_on = [module.snowflake_extractor]  # Commented out due to legacy module compatibility  # Commented out due to legacy module compatibility
}

# Create the Snowflake loader module
module "snowflake_loader" {
  source = "./modules/snowflake_loader"

  snowflake_account   = var.snowflake_account
  snowflake_username  = var.snowflake_username
  snowflake_password  = var.snowflake_password
  snowflake_role      = var.snowflake_role
  snowflake_warehouse = var.snowflake_warehouse
  snowflake_database  = var.snowflake_target_database
  snowflake_schema    = var.snowflake_target_schema
  target_table        = var.target_table

  s3_bucket         = aws_s3_bucket.entity_resolution_data.bucket
  s3_output_prefix  = var.s3_output_prefix
  aws_region        = var.aws_region
  entity_attributes = var.entity_attributes

  loader_glue_job_name = var.loader_glue_job_name
  glue_iam_role        = aws_iam_role.glue_role.arn
  loading_schedule     = var.loading_schedule

  tags = var.resource_tags

  # # depends_on = [module.entity_resolution]  # Commented out due to legacy module compatibility  # Commented out due to legacy module compatibility
}
