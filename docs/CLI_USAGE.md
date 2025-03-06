# AWS Entity Resolution CLI Usage Guide

This guide provides detailed instructions for using the AWS Entity Resolution CLI tool. The CLI provides a user-friendly interface for interacting with the AWS Entity Resolution pipeline.

## Installation

The CLI is installed as part of the AWS Entity Resolution package:

```bash
# Install from PyPI
pip install aws-entity-resolution

# Or install from source
git clone https://github.com/yourusername/aws-entity-resolution.git
cd aws-entity-resolution
pip install -e .
```

## Configuration

The CLI supports multiple configuration methods:

1. YAML/JSON configuration files
2. Environment variables
3. AWS Secrets Manager secrets

### Configuration File

The recommended approach is to use a YAML configuration file:

```yaml
# General settings
environment: prod
log_level: INFO

# AWS Configuration
aws:
  region: us-east-1
  profile: default

# S3 Configuration
s3:
  bucket: your-entity-resolution-bucket
  prefix: data/
  input_prefix: input/
  output_prefix: output/

# Entity Resolution Configuration
entity_resolution:
  workflow_id: your-workflow-id
  workflow_name: your-workflow-name
  schema_name: your-schema-name
  matching_threshold: 0.9
  reconciliation_mode: CHOOSE_FIRST_SOURCE

# Snowflake Target Configuration
snowflake_target:
  account: your-target-account
  username: your-target-user
  password: your-target-password
  role: your-target-role
  warehouse: your-target-warehouse
  database: your-target-database
  schema: your-target-schema
  table: your-target-table
```

### Environment Variables

You can set these in a `.env` file or directly in your environment.

#### Required Configuration

At minimum, you need to configure:

1. AWS credentials and region
2. S3 bucket for data storage
3. Glue database and table settings
4. Snowflake connection details (for loading results)
5. Entity Resolution workflow ID

Example `.env` file:

```
# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-entity-resolution-bucket

# Glue Configuration
GLUE_DATABASE=your-glue-database
GLUE_TABLE=your-source-table
S3_SOURCE_PATH=s3://your-bucket/your-source-path/

# Snowflake Target Configuration
SNOWFLAKE_TARGET_ACCOUNT=your-target-account
SNOWFLAKE_TARGET_USER=your-target-user
SNOWFLAKE_TARGET_PASSWORD=your-target-password
SNOWFLAKE_TARGET_WAREHOUSE=your-target-warehouse
SNOWFLAKE_TARGET_DATABASE=your-target-database
SNOWFLAKE_TARGET_SCHEMA=your-target-schema
TARGET_TABLE=your-target-table

# Entity Resolution Configuration
ENTITY_RESOLUTION_WORKFLOW_ID=your-workflow-id
```

### AWS Secrets Manager

For production environments, you can store configuration in AWS Secrets Manager:

```json
{
  "environment": "prod",
  "aws": {
    "region": "us-east-1"
  },
  "s3": {
    "bucket": "your-entity-resolution-bucket",
    "prefix": "data/"
  },
  "entity_resolution": {
    "workflow_id": "your-workflow-id",
    "schema_name": "your-schema-name"
  },
  "snowflake_target": {
    "account": "your-target-account",
    "username": "your-target-user",
    "password": "your-target-password",
    "warehouse": "your-target-warehouse",
    "database": "your-target-database",
    "schema": "your-target-schema",
    "table": "your-target-table"
  }
}
```

### Using a Custom Configuration File

You can specify a custom configuration file using the `--config` option:

```bash
aws-entity-resolution --config my-config.yaml process run
```

### Using AWS Secrets Manager

You can specify an AWS Secrets Manager secret using the `--secrets-name` option:

```bash
aws-entity-resolution --secrets-name entity-resolution/prod process run
```

## Data Flow Architecture

The AWS Entity Resolution pipeline operates with this flow:

1. Upstream processes export data from Snowflake to S3 (not part of this application)
2. This application creates Glue tables on top of the S3 data
3. Entity Resolution reads from the Glue tables to perform matching
4. Results are written to S3
5. Results are loaded to Snowflake

## Processing Data

The `process` command processes data through AWS Entity Resolution.

### Glue Table Creation

Before processing, you need to create a Glue table on top of your S3 data:

```bash
# Create a Glue table pointing to S3 data
aws-entity-resolution glue create-table --database your-database --table your-table --s3-path s3://your-bucket/your-path/ --schema-file schema.json
```

### Basic Processing Usage

```bash
# Process data through Entity Resolution using a Glue table
aws-entity-resolution process run --glue-database your-database --glue-table your-table
```

### Options

- `--output-prefix`, `-o`: S3 prefix for output data (default: "output/")
- `--wait/--no-wait`: Wait for processing to complete (default: wait)
- `--timeout`, `-t`: Maximum time to wait in seconds (default: 3600)
- `--glue-database`, `-d`: Glue database name
- `--glue-table`, `-t`: Glue table name

### Examples

```bash
# Process with a custom output location
aws-entity-resolution process run --glue-database customer_db --glue-table customer_data --output-prefix results/matched/

# Start processing without waiting for completion
aws-entity-resolution process run --glue-database customer_db --glue-table customer_data --no-wait

# Set a custom timeout for waiting
aws-entity-resolution process run --glue-database customer_db --glue-table customer_data --timeout 7200
```

### Checking Job Status

```bash
# Check the status of a job
aws-entity-resolution process status er-job-123456789
```

## Loading Data

The `load` command loads processed data from S3 to Snowflake.

### Basic Usage

```bash
# Load data to the default target table
aws-entity-resolution load run output/matched.csv
```

### Options

- `--target-table`, `-t`: Override target table name from environment variable
- `--truncate`: Truncate target table before loading

### Examples

```bash
# Load to a specific table
aws-entity-resolution load run output/matched.csv --target-table GOLDEN_CUSTOMERS

# Truncate the table before loading
aws-entity-resolution load run output/matched.csv --truncate
```

### Setting Up Snowflake Table

```bash
# Set up the default target table
aws-entity-resolution load setup

# Set up a specific table
aws-entity-resolution load setup --target-table GOLDEN_CUSTOMERS

# Force recreation of an existing table
aws-entity-resolution load setup --force
```

## Global Options

These options apply to all commands:

- `--verbose`, `-v`: Enable verbose output
- `--config`, `-c`: Path to config file (default: .env)
- `--secrets-name`, `-s`: AWS Secrets Manager secret name

Example:

```bash
aws-entity-resolution --verbose --config prod.yaml process run
```

Or using AWS Secrets Manager:

```bash
aws-entity-resolution --verbose --secrets-name entity-resolution/prod process run
```

## Error Handling

The CLI provides detailed error messages when operations fail. Common errors include:

- Missing configuration: Ensure all required environment variables are set
- AWS permissions: Verify your AWS credentials have the necessary permissions
- Snowflake connectivity: Check your Snowflake credentials and network connectivity
- Entity Resolution workflow: Ensure your workflow ID exists and is configured correctly
- Glue table issues: Verify that your Glue table exists and has the correct schema

## Logging

The CLI logs detailed information about its operations. By default, logs are written to the console. Enable verbose mode for more detailed logging:

```bash
aws-entity-resolution --verbose process run
```

## Best Practices

1. **Monitor long-running jobs**: For large datasets, use `--no-wait` and check status separately
2. **Secure credentials**: Store sensitive credentials in AWS Secrets Manager rather than in environment variables
3. **Use appropriate Glue table settings**: Ensure your Glue table configuration matches your S3 data format
4. **Set appropriate timeouts**: Adjust the timeout based on the size of your data

## Troubleshooting

### Common Issues

1. **Connection errors**: Verify your AWS and Snowflake credentials
2. **Permission denied**: Check your IAM permissions for S3, Glue, and Entity Resolution
3. **Timeout errors**: Increase the timeout for large datasets
4. **Missing data**: Verify your source S3 data is available and properly formatted
5. **Schema mismatch**: Ensure your Entity Resolution workflow schema matches your Glue table schema
6. **Glue table errors**: Verify the Glue table exists and points to the correct S3 location

### Getting Help

For additional help, run:

```bash
aws-entity-resolution --help
aws-entity-resolution process --help
aws-entity-resolution load --help
```
