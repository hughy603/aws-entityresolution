locals {
  # Schema validation rules
  valid_types = [
    "STRING", "NUMBER", "DATE", "EMAIL", "PHONE", "ADDRESS", "ID", "URL"
  ]

  valid_sub_types = [
    "NONE", "NAME", "ADDRESS_LINE1", "ADDRESS_LINE2", "ADDRESS_LINE3", "CITY", "STATE", "COUNTRY", "POSTAL_CODE",
    "PHONE_NUMBER", "PHONE_COUNTRY_CODE", "PHONE_EXTENSION", "FULL_NAME", "FIRST_NAME", "MIDDLE_NAME", "LAST_NAME",
    "ADDRESS_FULL", "HOUSE_NUMBER", "STREET_NAME", "CARE_OF", "SITE_NAME", "SITE_NUMBER", "STREET_TYPE", "STREET_SUFFIX",
    "STREET_DIRECTION", "PO_BOX_NUMBER", "RURAL_ROUTE_NUMBER", "EMAIL_USER", "EMAIL_DOMAIN", "PROVIDER_ID"
  ]

  # Select schema based on configuration
  schema = var.use_schema_template ? (
    var.schema_templates[var.schema_template_name]
  ) : var.schema_definition

  # Validate schema attributes
  validated_attributes = [
    for attr in local.schema.attributes : {
      name      = attr.name
      type      = upper(attr.type)
      sub_type  = attr.sub_type != null ? upper(attr.sub_type) : "NONE"
      match_key = coalesce(attr.match_key, false)
      required  = coalesce(attr.required, false)
      array     = coalesce(attr.array, false)
    }
    if contains(local.valid_types, upper(attr.type)) &&
    (attr.sub_type == null || contains(local.valid_sub_types, upper(attr.sub_type)))
  ]

  # Schema metadata
  schema_name        = var.schema_name != "" ? var.schema_name : "${var.project_name}-${var.environment}-schema"
  schema_description = "Entity Resolution schema for ${var.project_name} (${var.environment})"
}

# CloudFormation stack for Entity Resolution schema
resource "aws_cloudformation_stack" "schema" {
  name = local.schema_name

  template_body = jsonencode({
    Resources = {
      EntityResolutionSchema = {
        Type = "AWS::EntityResolution::Schema"
        Properties = {
          SchemaName  = local.schema_name
          Description = local.schema_description
          Attributes = [
            for attr in local.validated_attributes : {
              Name     = attr.name
              Type     = attr.type
              SubType  = attr.sub_type
              MatchKey = attr.match_key
              Required = attr.required
              Array    = attr.array
            }
          ]
        }
      }
    }
    Outputs = {
      SchemaArn = {
        Value = { "Ref" = "EntityResolutionSchema" }
      }
    }
  })

  capabilities = ["CAPABILITY_IAM"]
  tags         = var.tags
}

# Store schema information in SSM parameter (for applications to consume)
resource "aws_ssm_parameter" "schema" {
  name        = "/${var.project_name}/${var.environment}/entity-resolution/schema"
  description = "Entity Resolution schema configuration"
  type        = "String"
  value = jsonencode({
    schema_name  = local.schema_name
    schema_arn   = aws_cloudformation_stack.schema.outputs["SchemaArn"]
    attributes   = local.validated_attributes
    match_keys   = [for attr in local.validated_attributes : attr.name if attr.match_key]
    last_updated = timestamp()
  })
  tags = var.tags
}
