# Documentation on how to customize schemas
# Terraform doesn't support true functions, so we use composition of locals

# This is a usage example that would appear in the main module
output "customization_example" {
  description = "Example of how to customize a schema template"
  value       = <<-EOT
    # To customize a schema:

    module "schema_templates" {
      source = "./modules/schema_templates"
    }

    locals {
      # Create a custom schema based on the customer template
      custom_customer_schema = {
        # Start with the base template
        schema_name = "retail_customer"
        description = "Retail customer schema with loyalty attributes"

        # Combine all the attributes we want
        attributes = concat(
          module.schema_templates.id_attributes,
          module.schema_templates.name_attributes,
          module.schema_templates.contact_attributes,

          # Add custom attributes
          [
            {
              name = "loyalty_id"
              type = "ACCOUNT_NUMBER"
              glue_type = "string"
              match_key = true
              description = "Customer loyalty program ID"
            },
            {
              name = "membership_level"
              type = "TEXT"
              glue_type = "string"
              match_key = false
              description = "Loyalty membership level"
            }
          ]
        )
      }
    }

    # Validate the schema
    module "custom_customer_schema" {
      source = "../schema_validator"
      schema = local.custom_customer_schema
    }
  EOT
}
