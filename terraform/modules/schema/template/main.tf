locals {
  template_path = "${path.module}/templates/${var.template_name}.json"
}

data "local_file" "schema_template" {
  filename = local.template_path
}

resource "aws_s3_object" "schema_template" {
  bucket       = "${var.config.project_name}-${var.config.environment}-templates"
  key          = "${var.template_name}.json"
  content      = data.local_file.schema_template.content
  content_type = "application/json"
  tags         = var.config.tags
}
