# IAM Role for Entity Resolution
resource "aws_iam_role" "entity_resolution_role" {
  name = var.entity_resolution_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "entityresolution.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Entity Resolution
resource "aws_iam_policy" "entity_resolution_policy" {
  name        = var.entity_resolution_policy_name
  description = "Policy for AWS Entity Resolution service"

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
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "entity_resolution_attachment" {
  role       = aws_iam_role.entity_resolution_role.name
  policy_arn = aws_iam_policy.entity_resolution_policy.arn
}

# Additional S3 permissions
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.entity_resolution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Entity Resolution Schema Mapping
resource "aws_entityresolution_schema_mapping" "entity_schema" {
  schema_name = var.schema_name
  description = "Schema mapping for entity resolution"

  mapped_input_fields = local.mapped_input_fields

  depends_on = [aws_iam_role_policy_attachment.entity_resolution_attachment]
}

# Local variable to define mapped input fields based on entity attributes
locals {
  attribute_type_map = {
    "id"      = "TEXT"
    "name"    = "NAME"
    "email"   = "EMAIL"
    "phone"   = "PHONE_NUMBER"
    "address" = "ADDRESS"
    "company" = "TEXT"
  }

  mapped_input_fields = [
    for attr in var.entity_attributes : {
      field_name = attr
      type       = lookup(local.attribute_type_map, lower(attr), "TEXT")
      group_name = "default"
      sub_type   = "NONE"
      match_key  = true
    }
  ]
}

# Entity Resolution Matching Workflow
resource "aws_entityresolution_matching_workflow" "entity_matching" {
  workflow_name = var.matching_workflow_name
  description   = "Matching workflow for entity resolution"

  input_source_config {
    input_source_arn = "arn:aws:s3:::${var.s3_bucket}"
  }

  output_source_config {
    output_s3_path      = "s3://${var.s3_bucket}/${var.output_s3_prefix}"
    apply_normalization = true
  }

  resolution_techniques {
    resolution_type = "RULE_MATCHING"

    # Rule for matching by email
    resolution_rules {
      rule = "EXACT"
      matching_keys {
        name = "EMAIL"
      }
    }

    # Rule for matching by phone number
    resolution_rules {
      rule = "EXACT"
      matching_keys {
        name = "PHONE_NUMBER"
      }
    }
  }

  role_arn   = aws_iam_role.entity_resolution_role.arn
  schema_arn = aws_entityresolution_schema_mapping.entity_schema.arn

  tags = var.tags
}

# Create a directory for Glue job scripts
resource "aws_s3_object" "entity_resolution_script" {
  bucket = var.s3_bucket
  key    = "scripts/entity_resolution_processor.py"
  source = "${path.module}/glue/entity_resolution_job.py"
  etag   = filemd5("${path.module}/glue/entity_resolution_job.py")
}

# Create AWS Glue job for processing Entity Resolution
resource "aws_glue_job" "entity_resolution_processor" {
  name         = var.glue_job_name
  role_arn     = var.glue_iam_role
  glue_version = "3.0"

  command {
    script_location = "s3://${var.s3_bucket}/${aws_s3_object.entity_resolution_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-job-insights"              = "true"
    "--job-language"                     = "python"
    "--TempDir"                          = "s3://${var.s3_bucket}/temp/"
    "--enable-spark-ui"                  = "true"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--s3_bucket"                        = var.s3_bucket
    "--input_s3_prefix"                  = var.input_s3_prefix
    "--output_s3_prefix"                 = var.output_s3_prefix
    "--workflow_name"                    = var.matching_workflow_name
    "--schema_name"                      = var.schema_name
    "--entity_attributes"                = join(",", var.entity_attributes)
    "--aws_region"                       = var.aws_region
    "--extra-py-files"                   = "s3://${var.s3_bucket}/python/aws_entity_resolution-0.1.0-py3-none-any.whl"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  timeout = 60 # minutes

  tags = var.tags
}

# Upload the Python package wheel file to S3
resource "aws_s3_object" "entity_resolution_wheel" {
  bucket = var.s3_bucket
  key    = "python/aws_entity_resolution-0.1.0-py3-none-any.whl"
  source = "${path.module}/../../../dist/aws_entity_resolution-0.1.0-py3-none-any.whl"
  etag   = filemd5("${path.module}/../../../dist/aws_entity_resolution-0.1.0-py3-none-any.whl")
}

# Ensure the Glue job depends on the wheel file being uploaded
resource "null_resource" "dependency_wheel" {
  triggers = {
    wheel_id = aws_s3_object.entity_resolution_wheel.id
  }
}

resource "null_resource" "dependency_glue_job" {
  triggers = {
    job_dependency = null_resource.dependency_wheel.id
    job_id         = aws_glue_job.entity_resolution_processor.id
  }
}
