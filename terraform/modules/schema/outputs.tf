output "schema" {
  description = "Entity Resolution schema details"
  value = {
    name        = local.schema_metadata.name
    description = local.schema_metadata.description
    attributes  = local.validated_attributes
    arn         = aws_cloudformation_stack.schema.outputs.SchemaArn
  }
}

output "glue_columns" {
  description = "Glue catalog column definitions"
  value       = local.glue_columns
}

output "er_mappings" {
  description = "Entity Resolution attribute mappings"
  value       = local.er_mappings
}

output "schema_template_used" {
  description = "Whether a schema template was used"
  value       = var.use_schema_template
}

output "schema_template_name" {
  description = "Name of the schema template used (if any)"
  value       = var.use_schema_template ? var.schema_template_name : null
}
