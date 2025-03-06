# Entity Resolution Schema Templates

This module provides reusable schema templates for Entity Resolution and Glue Table definitions. It allows for faster schema creation with consistent attribute definitions.

## Features

- Pre-defined templates for common entity types
- Reusable attribute sets (identifiers, names, contact info, etc.)
- Easy composition of custom schemas from attribute building blocks

## Available Templates

### Entity Templates

- **Person Template**: Basic person schema with ID, name, and contact information
- **Customer Template**: Extended person schema with customer-specific attributes
- **Employee Template**: Extended person schema with employee-specific attributes

### Attribute Sets

- **id_attributes**: Common identifier attributes
- **name_attributes**: First and last name attributes
- **contact_attributes**: Email and phone attributes
- **address_attributes**: Address attributes
- **timestamp_attributes**: Creation timestamp attributes

## Usage

### Using a complete template:

```hcl
module "schema_templates" {
  source = "./modules/schema_templates"
}

module "schema_validator" {
  source = "./modules/schema_validator"
  schema = module.schema_templates.customer_template
}
```

### Creating a custom schema by combining attribute sets:

```hcl
module "schema_templates" {
  source = "./modules/schema_templates"
}

locals {
  # Create a custom schema
  custom_schema = {
    schema_name = "custom_entity"
    description = "Custom entity schema"

    # Combine attribute sets
    attributes = concat(
      module.schema_templates.id_attributes,
      module.schema_templates.name_attributes,

      # Add custom attributes
      [
        {
          name = "custom_field"
          type = "TEXT"
          glue_type = "string"
          match_key = false
          description = "Custom field"
        }
      ]
    )
  }
}

# Validate the custom schema
module "schema_validator" {
  source = "./modules/schema_validator"
  schema = local.custom_schema
}
```

## Template Structures

### Person Template

```json
{
  "schema_name": "person",
  "description": "Generic person schema",
  "attributes": [
    {"name": "id", "type": "PERSON_IDENTIFIER", ...},
    {"name": "first_name", "type": "NAME", "subtype": "FIRST", ...},
    {"name": "last_name", "type": "NAME", "subtype": "LAST", ...},
    {"name": "email", "type": "EMAIL", ...},
    {"name": "phone", "type": "PHONE_NUMBER", ...},
    {"name": "created_at", "type": "DATE", ...}
  ]
}
```

### Customer Template

```json
{
  "schema_name": "customer",
  "description": "Customer schema for matching",
  "attributes": [
    {"name": "id", "type": "PERSON_IDENTIFIER", ...},
    {"name": "first_name", "type": "NAME", "subtype": "FIRST", ...},
    {"name": "last_name", "type": "NAME", "subtype": "LAST", ...},
    {"name": "email", "type": "EMAIL", ...},
    {"name": "phone", "type": "PHONE_NUMBER", ...},
    {"name": "address", "type": "ADDRESS", ...},
    {"name": "created_at", "type": "DATE", ...},
    {"name": "customer_type", "type": "TEXT", ...}
  ]
}
```

## Integration

### Combined with Schema Validator:

```hcl
# Use template or customize it
locals {
  schema = module.schema_templates.customer_template
}

# Validate the schema
module "schema_validator" {
  source = "./modules/schema_validator"
  schema = local.schema
}

# Use the validated schema
resource "aws_glue_catalog_table" "entity_table" {
  # ... configuration using module.schema_validator outputs
}
```
