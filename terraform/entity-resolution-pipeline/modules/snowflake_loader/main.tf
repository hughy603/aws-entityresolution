# Secret Manager for storing Snowflake credentials securely
resource "aws_secretsmanager_secret" "snowflake_credentials" {
  name        = "snowflake-credentials-for-entity-resolution-loader"
  description = "Snowflake credentials for loading resolved entity data"
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

# Create target table in Snowflake if it doesn't exist
resource "snowflake_table" "golden_records" {
  database = var.snowflake_database
  schema   = var.snowflake_schema
  name     = var.target_table
  comment  = "Golden entity records created through AWS Entity Resolution"

  column {
    name     = "ID"
    type     = "VARCHAR"
    nullable = false
  }

  column {
    name     = "ENTITY_ID"
    type     = "VARCHAR"
    nullable = false
    comment  = "Unique entity ID assigned by Entity Resolution"
  }

  column {
    name     = "NAME"
    type     = "VARCHAR"
    nullable = true
  }

  column {
    name     = "EMAIL"
    type     = "VARCHAR"
    nullable = true
  }

  column {
    name     = "PHONE"
    type     = "VARCHAR"
    nullable = true
  }

  column {
    name     = "ADDRESS"
    type     = "VARCHAR"
    nullable = true
  }

  column {
    name     = "COMPANY"
    type     = "VARCHAR"
    nullable = true
  }

  column {
    name     = "SOURCE_ID"
    type     = "VARCHAR"
    nullable = true
    comment  = "Original record ID from source system"
  }

  column {
    name     = "IS_GOLDEN_RECORD"
    type     = "BOOLEAN"
    nullable = false
    default {
      constant = "FALSE"
    }
  }

  column {
    name     = "LOADED_AT"
    type     = "TIMESTAMP_NTZ"
    nullable = false
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }

  primary_key {
    keys = ["ID"]
  }
}

# Prepare Glue resources
resource "aws_s3_object" "loader_script" {
  bucket = var.s3_bucket
  key    = "scripts/s3_to_snowflake_loader.py"
  content = templatefile("${path.module}/templates/s3_to_snowflake_loader.py.tpl", {
    snowflake_credentials_secret = aws_secretsmanager_secret.snowflake_credentials.name
    target_table                 = var.target_table
    entity_attributes            = var.entity_attributes
    s3_bucket                    = var.s3_bucket
    s3_output_prefix             = var.s3_output_prefix
    region                       = var.aws_region
  })
}

# Create AWS Glue job for loading data to Snowflake
resource "aws_glue_job" "s3_to_snowflake" {
  name         = var.loader_glue_job_name
  role_arn     = var.glue_iam_role
  glue_version = "3.0"

  command {
    script_location = "s3://${var.s3_bucket}/${aws_s3_object.loader_script.key}"
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
    "--target_table"                     = var.target_table
    "--s3_bucket"                        = var.s3_bucket
    "--s3_output_prefix"                 = var.s3_output_prefix
  }

  execution_property {
    max_concurrent_runs = 1
  }

  timeout = 60 # minutes

  tags = var.tags
}

# Create trigger for scheduled execution
resource "aws_glue_trigger" "snowflake_loading_schedule" {
  name     = "${var.loader_glue_job_name}-trigger"
  type     = "SCHEDULED"
  schedule = var.loading_schedule

  actions {
    job_name = aws_glue_job.s3_to_snowflake.name
  }

  tags = var.tags
}
