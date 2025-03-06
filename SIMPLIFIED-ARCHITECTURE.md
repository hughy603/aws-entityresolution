# AWS Entity Resolution - Simplified Architecture

This document outlines the simplified approach for separation of concerns between Python application code and infrastructure code (Terraform) in the AWS Entity Resolution project.

## Key Principles

1. **Clear Ownership Boundaries**:
   - **Infrastructure (Terraform)**: Owns all AWS resource creation and configuration
   - **Application (Python)**: Consumes AWS resources and focuses on data processing

2. **Single Source of Truth**:
   - Schema definitions live exclusively in Terraform
   - SSM Parameters expose schema information to applications
   - No duplication of configuration or validation logic

3. **Minimal Coupling**:
   - Application code doesn't need to know how infrastructure is configured
   - Infrastructure doesn't need to adapt to application implementation details

## Architecture Components

### 1. Infrastructure Layer (Terraform)

The infrastructure layer is responsible for:

- Creating and managing AWS Entity Resolution schemas and workflows
- Storing configuration in SSM Parameter Store
- Setting up IAM roles and permissions
- Creating S3 buckets for data storage

Key modules:
- `schema`: Defines and validates Entity Resolution schemas
- `entity-resolution-pipeline`: Sets up the data processing pipeline

### 2. Application Layer (Python)

The application layer is responsible for:

- Retrieving schema information from AWS
- Processing data according to the schema
- Loading data to target systems

Key modules:
- `services/entity_resolution.py`: Simple functions to interact with AWS Entity Resolution
- `loader/snowflake_loader.py`: Functions to load Entity Resolution output to Snowflake

## Implementation Details

### Schema Management

1. **Schema Definition (Terraform)**:
   ```terraform
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
     })
   }
   ```

2. **Schema Exposure (Terraform)**:
   ```terraform
   resource "aws_ssm_parameter" "schema" {
     name  = "/${var.project_name}/${var.environment}/entity-resolution/schema"
     type  = "String"
     value = jsonencode({
       schema_name  = local.schema_name
       schema_arn   = aws_cloudformation_stack.schema.outputs["SchemaArn"]
       attributes   = local.validated_attributes
       match_keys   = [for attr in local.validated_attributes : attr.name if attr.match_key]
       last_updated = timestamp()
     })
   }
   ```

3. **Schema Consumption (Python)**:
   ```python
   def get_schema(schema_name: str) -> Dict[str, Any]:
       """Get Entity Resolution schema from AWS."""
       client = boto3.client('entityresolution')
       response = client.get_schema(schemaName=schema_name)
       return {
           "schema_name": schema_name,
           "schema_arn": response.get("schemaArn", ""),
           "attributes": [
               {
                   "name": attr.get("name"),
                   "type": attr.get("type"),
                   "subtype": attr.get("subType", "NONE"),
                   "match_key": attr.get("matchKey", False),
               }
               for attr in response.get("attributes", [])
           ]
       }
   ```

### Data Loading

1. **Dynamic Table Creation (Python)**:
   ```python
   def get_table_columns_from_schema(schema_name: str) -> List[str]:
       """Get table column definitions from Entity Resolution schema."""
       # Get schema from AWS
       schema_info = get_schema(schema_name)

       # Create column definitions based on attribute types
       columns = []
       for attr in schema_info.get("attributes", []):
           name = attr.get("name")
           attr_type = attr.get("type")

           # Map Entity Resolution types to Snowflake types
           if attr_type == "STRING":
               sf_type = "VARCHAR"
           elif attr_type == "NUMBER":
               sf_type = "FLOAT"
           # ...etc.

           columns.append(f"{name.upper()} {sf_type}")

       return columns
   ```

## Benefits of This Approach

1. **Simplicity**:
   - Clear, focused components with single responsibilities
   - No complicated abstractions or interfaces
   - Easier to understand and maintain

2. **Flexibility**:
   - Infrastructure can evolve independently
   - Application can adapt to schema changes automatically
   - Easy to extend for new use cases

3. **Maintainability**:
   - Less code to maintain
   - Clear ownership boundaries
   - Fewer dependencies between components

## Next Steps

1. **Testing**:
   - Add unit tests for Python components
   - Add validation tests for Terraform configurations

2. **Documentation**:
   - Document the interfaces between layers
   - Create usage examples for developers

3. **Automation**:
   - Add CI/CD pipelines for continuous validation
