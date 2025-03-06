output "validated_schema" {
  description = "Validated schema"
  value       = var.schema
}

output "validated_schema_name" {
  description = "The validated schema name (will be empty string if not provided in schema)"
  value       = try(var.schema.schema_name, "")
}

output "validated_description" {
  description = "The validated schema description"
  value       = try(var.schema.description, "")
}

output "validated_workflow_name" {
  description = "The validated workflow name (will be empty string if not provided in schema)"
  value       = try(var.schema.workflow_name, "")
}

output "validated_attributes" {
  description = "List of validated schema attributes"
  value       = var.schema.attributes
}

output "validated_glue_columns" {
  description = "Formatted Glue columns derived from validated schema attributes"
  value = [
    for attr in var.schema.attributes : {
      name    = attr.name
      type    = attr.glue_type
      comment = try(attr.description, "")
    }
  ]
}

output "validated_er_mappings" {
  description = "Formatted Entity Resolution mappings derived from validated schema attributes"
  value = [
    for attr in var.schema.attributes : {
      name      = attr.name
      type      = attr.type
      subtype   = try(attr.subtype, null)
      match_key = try(attr.match_key, false)
    }
  ]
}

output "validated_attribute_names" {
  description = "List of validated attribute names"
  value       = [for attr in var.schema.attributes : attr.name]
}

output "validated_attributes_comma_separated" {
  description = "Comma-separated list of validated attribute names"
  value       = join(",", [for attr in var.schema.attributes : attr.name])
}
