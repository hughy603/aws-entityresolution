# Secret Manager for storing Snowflake credentials securely
resource "aws_secretsmanager_secret" "snowflake_credentials" {
  name        = "snowflake-credentials-for-entity-resolution"
  description = "Snowflake credentials for entity resolution data extraction"
  tags        = var.tags
}

resource "aws_secretsmanager_secret_version" "snowflake_credentials" {
  secret_id = aws_secretsmanager_secret.snowflake_credentials.id
  secret_string = jsonencode({
    account   = var.snowflake_account
    username  = var.snowflake_username
    password  = var.snowflake_password
    warehouse = var.snowflake_warehouse
    database  = var.snowflake_database
    schema    = var.snowflake_schema
    role      = var.snowflake_role
  })
}

# Prepare Glue resources
resource "aws_s3_bucket_object" "extraction_script" {
  bucket = var.s3_bucket
  key    = "scripts/snowflake_to_s3_extraction.py"
  content = templatefile("${path.module}/templates/snowflake_to_s3_extraction.py.tpl", {
    snowflake_credentials_secret = aws_secretsmanager_secret.snowflake_credentials.name
    source_table                 = var.source_table
    entity_attributes            = var.entity_attributes
    s3_bucket                    = var.s3_bucket
    s3_prefix                    = var.s3_prefix
    region                       = var.aws_region
  })
}

# Create AWS Glue job for extraction
resource "aws_glue_job" "snowflake_to_s3" {
  name         = var.extraction_glue_job_name
  role_arn     = var.glue_iam_role
  glue_version = "3.0"

  command {
    script_location = "s3://${var.s3_bucket}/${aws_s3_bucket_object.extraction_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-job-insights"              = "true"
    "--job-language"                     = "python"
    "--TempDir"                          = "s3://${var.s3_bucket}/temp/"
    "--enable-spark-ui"                  = "true"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--snowflake_credentials_secret"     = aws_secretsmanager_secret.snowflake_credentials.name
    "--source_table"                     = var.source_table
    "--s3_bucket"                        = var.s3_bucket
    "--s3_prefix"                        = var.s3_prefix
  }

  execution_property {
    max_concurrent_runs = 1
  }

  timeout = 60 # minutes

  tags = var.tags
}

# Create trigger for scheduled execution
resource "aws_glue_trigger" "snowflake_extraction_schedule" {
  name     = "${var.extraction_glue_job_name}-trigger"
  type     = "SCHEDULED"
  schedule = var.extraction_schedule

  actions {
    job_name = aws_glue_job.snowflake_to_s3.name
  }

  tags = var.tags
}
