# AWS Entity Resolution Schema Validator

This Terraform module validates schema definitions for AWS Entity Resolution and AWS Glue tables. It ensures that attribute definitions follow the required structure and contain valid attribute types for both AWS Entity Resolution and AWS Glue.

## Features

- Validates schema structure for Entity Resolution and Glue Table definitions
- Makes `schema_name`, `description`, and `workflow_name` optional fields
- Ensures each attribute has the required properties
- Validates that attribute types are acceptable for Entity Resolution
- Validates that Glue types are valid
- Provides formatted outputs for both Glue and CloudFormation resources

## Usage

### Basic Example with Simplified Schema

The simplified approach allows you to define only attributes in your JSON schema file and provide metadata separately in your Terraform configuration:

```hcl
# In your JSON file (schemas/person_schema.json):
{
  "attributes": [
    {
      "name": "id",
      "type": "PERSON_IDENTIFIER",
      "glue_type": "string",
      "match_key": true
    },
    {
      "name": "first_name",
      "type": "NAME",
      "subtype": "FIRST",
      "glue_type": "string",
      "match_key": true
    },
    # ...more attributes
  ]
}

# In your Terraform file:
locals {
  # Define schema metadata separately
  schema_metadata = {
    schema_name   = "person_schema"
    description   = "Person entity schema for matching"
    workflow_name = "person-matching-workflow"
  }

  # Load attributes from JSON and combine with metadata
  schema = {
    schema_name   = local.schema_metadata.schema_name
    description   = local.schema_metadata.description
    workflow_name = local.schema_metadata.workflow_name
    attributes    = jsondecode(file("schemas/person_schema.json")).attributes
  }
}

module "schema_validator" {
  source = "./modules/schema_validator"
  schema = local.schema
}
```

### JSON Schema Structure

The simplified JSON schema structure only requires the `attributes` field:

```json
{
  "attributes": [
    {
      "name": "id",
      "type": "PERSON_IDENTIFIER",
      "glue_type": "string",
      "match_key": true,
      "description": "Optional description"
    },
    ...
  ]
}
```

While the module's internal schema structure supports these fields (all optional except attributes):
```
{
  schema_name: string (optional)
  description: string (optional)
  workflow_name: string (optional)
  attributes: [] (required)
}
```

### Attribute Properties

Each attribute requires the following properties:

| Property     | Required | Description                                |
|--------------|----------|--------------------------------------------|
| name         | Yes      | Name of the attribute                      |
| type         | Yes      | Entity Resolution type                     |
| subtype      | No       | Entity Resolution subtype (for some types) |
| glue_type    | Yes      | AWS Glue data type                         |
| match_key    | No       | Whether to use for matching (default false)|
| description  | No       | Optional description of the attribute      |

## Valid Attribute Types

### Entity Resolution Types

- `NAME`: Name of a person (subtypes: `FIRST`, `MIDDLE`, `LAST`)
- `EMAIL`: Email address
- `PHONE_NUMBER`: Phone number
- `ADDRESS`: Physical address
- `PERSON_IDENTIFIER`: Unique identifier for a person
- `DATE`: Date field (such as birth date)
- `TEXT`: Generic text field
- ...and others defined in AWS Entity Resolution service

### Glue Types

- `string`
- `int`
- `bigint`
- `double`
- `boolean`
- `date`
- `timestamp`
- `decimal`
- `array<data_type>`
- `map<primitive_type,data_type>`
- `struct<...>`

## Outputs

| Output                              | Description                                      |
|-------------------------------------|--------------------------------------------------|
| validated_schema_name               | Validated schema name (empty string if not provided) |
| validated_description               | Validated schema description (empty string if not provided) |
| validated_workflow_name             | Validated workflow name (empty string if not provided) |
| validated_attributes                | List of validated schema attributes             |
| validated_glue_columns              | Formatted AWS Glue columns configuration        |
| validated_er_mappings               | Formatted Entity Resolution field mappings      |
| validated_attribute_names           | List of validated attribute names               |
| validated_attributes_comma_separated| Comma-separated list of attribute names         |

## Integration Example

### AWS Glue Catalog Table

```hcl
resource "aws_glue_catalog_table" "entity_table" {
  name          = "person_data"
  database_name = "entity_resolution_db"

  storage_descriptor {
    dynamic "columns" {
      for_each = module.schema_validator.validated_glue_columns
      content {
        name    = columns.value.name
        type    = columns.value.type
        comment = columns.value.comment
      }
    }

    # Other storage settings...
  }
}
```

### AWS CloudFormation for Entity Resolution

```hcl
resource "aws_cloudformation_stack" "entity_resolution" {
  name = "${module.schema_validator.validated_workflow_name}-stack"

  template_body = jsonencode({
    Resources = {
      EntityResolutionMatchingWorkflow = {
        Type = "AWS::EntityResolution::MatchingWorkflow"
        Properties = {
          WorkflowName      = module.schema_validator.validated_workflow_name
          Description       = module.schema_validator.validated_description
          InputSourceConfig = {
            InputSourceARN  = aws_glue_catalog_table.entity_table.arn
            SchemaName      = module.schema_validator.validated_schema_name
            InputSourceConfig = {
              for attribute in module.schema_validator.validated_er_mappings :
              attribute.name => {
                MatchKey = attribute.match_key
                Type     = attribute.type
                SubType  = try(attribute.subtype, null)
              }
            }
          }
          # Other configuration...
        }
      }
    }
  })
}
