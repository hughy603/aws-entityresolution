# AWS Entity Resolution Solution

This repository contains a complete solution for entity resolution using AWS services. It provides:

1. **CloudFormation Service Catalog Product**: Deployable through Service Catalog for provisioning AWS Entity Resolution infrastructure
2. **Terraform Pipeline**: A Terraform-based data pipeline that extracts from Snowflake, processes with AWS Entity Resolution, and loads back to Snowflake
3. **Python CLI Tool**: A command-line interface for interacting with the AWS Entity Resolution pipeline

## CloudFormation Service Catalog Product

The CloudFormation Service Catalog product in `cloudformation/entity-resolution-product/` includes:

- Entity resolution template that creates the underlying infrastructure
- Service Catalog product definition
- Documentation for users

### Key Features:

- Pre-configured AWS Entity Resolution workflow
- Rule-based matching for entity resolution
- Customizable schema for entity attributes
- S3 integration for entity data storage
- IAM roles and permissions

## Terraform Entity Resolution Pipeline

The Terraform pipeline in `terraform/entity-resolution-pipeline/` includes:

- Complete end-to-end pipeline for entity resolution
- Snowflake extractor module
- AWS Entity Resolution module
- Snowflake loader module for golden records

### Key Features:

- Extracts entity data from Snowflake
- Processes through AWS Entity Resolution
- Loads resolved data back to Snowflake
- Scheduled execution via AWS Glue
- Secure credential management

## Python CLI Tool

The Python CLI tool provides a convenient way to interact with the AWS Entity Resolution pipeline. It allows you to:

- Extract data from Snowflake to S3
- Process data through AWS Entity Resolution
- Load matched records back to Snowflake
- Run the complete pipeline in a single command

### Key Features:

- Unified CLI interface for all pipeline stages
- Configuration through environment variables or config files
- Dry-run mode for testing without executing
- Detailed logging and error handling
- Support for custom SQL queries and table overrides

### Installation

```bash
# Install using pip
pip install aws-entity-resolution

# Or install from source
git clone https://github.com/yourusername/aws-entity-resolution.git
cd aws-entity-resolution
pip install -e .
```

### Usage

```bash
# Run the complete pipeline
entity-resolution run-pipeline

# Extract data from Snowflake to S3
entity-resolution extract run

# Process data through AWS Entity Resolution
entity-resolution process run

# Load matched records to Snowflake
entity-resolution load run

# Show help
entity-resolution --help
```

## Getting Started

### Service Catalog Product Deployment

1. Navigate to the `cloudformation/entity-resolution-product/` directory
2. Follow the instructions in the README file to upload and deploy the CloudFormation templates

### Terraform Pipeline Deployment

1. Navigate to the `terraform/entity-resolution-pipeline/` directory
2. Follow the instructions in the README file to configure and deploy the Terraform pipeline

## Architecture

### Service Catalog Product

The Service Catalog product creates:
- AWS Entity Resolution schema mapping
- Entity Resolution matching workflow
- S3 bucket for entity data
- IAM roles and permissions

### Terraform Pipeline

The Terraform pipeline creates:
- Glue jobs for data extraction and loading
- S3 bucket for entity data
- AWS Entity Resolution configuration
- IAM roles and permissions
- Snowflake table for golden records

## Security Considerations

- All S3 buckets have encryption enabled and public access blocked
- IAM roles follow the principle of least privilege
- Snowflake credentials are stored securely in AWS Secrets Manager
- All sensitive data is encrypted both in transit and at rest

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Development

### Code Quality Tools

This project uses several tools to maintain code quality:

- **Ruff**: Used for linting and import sorting. Replaces isort for managing imports.
- **Black**: Used for code formatting.
- **MyPy**: Used for static type checking.
- **Pre-commit**: Used to run linters and formatters before commits.

### Running Code Quality Tools

To fix imports using Ruff:

```bash
# Run the import fixing script
./fix_imports.py

# Or use Ruff directly
poetry run ruff check --select=I --fix src tests
```

To run all linters and formatters:

```bash
poetry run pre-commit run --all-files
```
