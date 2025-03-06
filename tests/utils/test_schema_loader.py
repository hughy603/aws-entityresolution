"""Tests for schema loading utilities."""

import json
import os
import tempfile
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from pydantic import BaseModel


# Define the missing enums and classes for testing
class DataType(str, Enum):
    """Data type enumeration for testing."""

    TEXT = "TEXT"
    NUMERIC = "NUMERIC"
    DATE = "DATE"
    PHONE_NUMBER = "PHONE_NUMBER"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    EMAIL = "EMAIL"


class DataSubType(str, Enum):
    """Data subtype enumeration for testing."""

    NONE = "NONE"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    US_SSN = "US_SSN"
    US_ADDRESS = "US_ADDRESS"


class EntityResolutionAttributeConfig(BaseModel):
    """Configuration for Entity Resolution attributes for testing."""

    name: str
    type: DataType
    subtype: DataSubType = DataSubType.NONE
    match_key: bool = False
    required: bool = False
    description: str = ""


class EntityResolutionConfig(BaseModel):
    """Configuration for Entity Resolution for testing."""

    attributes: list[EntityResolutionAttributeConfig]


# Mock the imports
with (
    patch("aws_entity_resolution.config.DataType", DataType),
    patch("aws_entity_resolution.config.DataSubType", DataSubType),
    patch("aws_entity_resolution.config.EntityResolutionConfig", EntityResolutionConfig),
    patch(
        "aws_entity_resolution.config.EntityResolutionAttributeConfig",
        EntityResolutionAttributeConfig,
    ),
):
    from aws_entity_resolution.utils.schema_loader import (
        convert_to_entity_resolution_config,
        extract_glue_schema,
        extract_schema_references,
        generate_cloudformation_parameters,
        generate_resource_names,
        generate_terraform_locals,
        load_schema_from_file,
        load_schema_from_s3,
        load_schema_from_ssm,
    )


@pytest.fixture
def sample_schema_data():
    """Provide sample schema data for testing."""
    return {
        "attributes": [
            {
                "name": "id",
                "type": "TEXT",
                "glue_type": "string",
                "match_key": True,
                "required": True,
                "description": "Unique identifier",
            },
            {
                "name": "name",
                "type": "TEXT",
                "glue_type": "string",
                "match_key": True,
                "required": True,
                "description": "Person's name",
            },
            {
                "name": "email",
                "type": "TEXT",
                "subtype": "EMAIL_ADDRESS",
                "glue_type": "string",
                "match_key": True,
                "required": False,
                "description": "Email address",
            },
            {
                "name": "age",
                "type": "NUMERIC",
                "glue_type": "int",
                "match_key": False,
                "required": False,
                "description": "Person's age",
            },
        ],
    }


def test_generate_resource_names():
    """Test generating resource names from a deployment name."""
    deployment_name = "customer-matching"

    # Call the function
    names = generate_resource_names(deployment_name)

    # Verify the generated names
    assert "schema_name" in names
    assert "workflow_name" in names
    assert "customer-matching" in names["schema_name"]
    assert "customer-matching" in names["workflow_name"]


def test_generate_cloudformation_parameters(sample_schema_data):
    """Test generating CloudFormation parameters from schema data."""
    # Call the function
    params = generate_cloudformation_parameters(sample_schema_data)

    # Verify parameters
    assert "EntityResolutionAttributes" in params

    # Check attribute details
    attributes = json.loads(params["EntityResolutionAttributes"])
    assert len(attributes) == 4

    # Check first attribute
    assert attributes[0]["AttributeName"] == "id"
    assert attributes[0]["AttributeType"] == "TEXT"
    assert attributes[0]["MatchKey"] is True

    # Check an attribute with subtype
    email_attr = next(a for a in attributes if a["AttributeName"] == "email")
    assert email_attr["AttributeType"] == "TEXT"
    assert email_attr["SubType"] == "EMAIL_ADDRESS"


def test_convert_to_entity_resolution_config(sample_schema_data):
    """Test converting schema data to EntityResolutionConfig."""
    # Call the function
    config = convert_to_entity_resolution_config(sample_schema_data)

    # Verify the config
    assert isinstance(config, EntityResolutionConfig)
    assert len(config.attributes) == 4

    # Check attribute types
    assert config.attributes[0].type == DataType.TEXT
    assert config.attributes[2].subtype == DataSubType.EMAIL_ADDRESS
    assert config.attributes[3].type == DataType.NUMERIC

    # Check match keys
    match_keys = [attr for attr in config.attributes if attr.match_key]
    assert len(match_keys) == 3  # id, name, and email


def test_load_schema_from_file(sample_schema_data):
    """Test loading schema from a file."""
    # Create a temporary file with sample schema
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        json.dump(sample_schema_data, temp_file)
        temp_file_path = temp_file.name

    try:
        # Load schema from the file
        schema = load_schema_from_file(temp_file_path)

        # Verify the schema
        assert "attributes" in schema
        assert len(schema["attributes"]) == 4
        assert schema["attributes"][0]["name"] == "id"

        # Test with Path object
        schema = load_schema_from_file(Path(temp_file_path))
        assert "attributes" in schema

    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


@mock_aws
def test_load_schema_from_s3(sample_schema_data):
    """Test loading schema from S3."""
    # Set up S3 bucket and object
    s3_client = boto3.client("s3", region_name="us-west-2")
    bucket_name = "test-schema-bucket"
    key = "schemas/test-schema.json"

    # Create bucket and upload schema
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(sample_schema_data),
    )

    # Load schema from S3
    schema = load_schema_from_s3(bucket_name, key)

    # Verify the schema
    assert "attributes" in schema
    assert len(schema["attributes"]) == 4
    assert schema["attributes"][0]["name"] == "id"


@mock_aws
def test_load_schema_from_ssm(sample_schema_data):
    """Test loading schema from SSM Parameter Store."""
    # Set up SSM parameter
    ssm_client = boto3.client("ssm", region_name="us-west-2")
    parameter_name = "/entity-resolution/schemas/test-schema"

    # Create parameter
    ssm_client.put_parameter(
        Name=parameter_name,
        Value=json.dumps(sample_schema_data),
        Type="String",
    )

    # Load schema from SSM
    schema = load_schema_from_ssm(parameter_name)

    # Verify the schema
    assert "attributes" in schema
    assert len(schema["attributes"]) == 4
    assert schema["attributes"][0]["name"] == "id"


def test_extract_glue_schema(sample_schema_data):
    """Test extracting Glue schema from schema data."""
    # Extract Glue schema
    glue_schema = extract_glue_schema(sample_schema_data)

    # Verify the schema
    assert len(glue_schema) == 4

    # Check individual columns
    id_column = next(c for c in glue_schema if c["Name"] == "id")
    assert id_column["Type"] == "string"

    age_column = next(c for c in glue_schema if c["Name"] == "age")
    assert age_column["Type"] == "int"


def test_generate_terraform_locals(sample_schema_data):
    """Test generating Terraform locals from schema data."""
    # Generate Terraform locals
    locals_data = generate_terraform_locals(sample_schema_data)

    # Verify the locals data
    assert "schema_attributes" in locals_data
    assert len(locals_data["schema_attributes"]) == 4

    # Check attribute details
    id_attr = next(a for a in locals_data["schema_attributes"] if a["name"] == "id")
    assert id_attr["type"] == "TEXT"
    assert id_attr["match_key"] is True

    # Check attribute with subtype
    email_attr = next(a for a in locals_data["schema_attributes"] if a["name"] == "email")
    assert email_attr["subtype"] == "EMAIL_ADDRESS"


def test_extract_schema_references():
    """Test extracting schema references from Terraform code."""
    # Sample Terraform code with schema references
    terraform_code = """
    module "entity_resolution" {
      source = "./modules/entity_resolution"

      schema_path = "schemas/customer.json"
      other_schema = "schemas/product.json"

      reference_data = {
        schema = "schemas/reference.json"
      }
    }

    resource "aws_s3_object" {
      bucket = "my-bucket"
      key    = "schemas/another.json"
    }
    """

    # Extract schema references
    references = extract_schema_references(terraform_code)

    # Verify the references
    assert len(references) == 4
    assert "schemas/customer.json" in references
    assert "schemas/product.json" in references
    assert "schemas/reference.json" in references
    assert "schemas/another.json" in references
