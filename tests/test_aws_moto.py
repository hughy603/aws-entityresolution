"""Tests for AWS services using moto for mocking."""

import boto3
import pytest
from moto import mock_aws

from aws_entity_resolution.config import Settings
from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.s3 import S3Service


@pytest.fixture
def aws_credentials():
    """Set up mock AWS credentials for tests."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    yield

    # Clean up
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    os.environ.pop("AWS_SECURITY_TOKEN", None)
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ.pop("AWS_DEFAULT_REGION", None)
    os.environ.pop("AWS_REGION", None)


@pytest.fixture
def s3_test_bucket(aws_credentials):
    """Create a test S3 bucket using moto."""
    with mock_aws():
        # Create a bucket
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-entity-resolution-bucket"
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

        # Create a test file
        s3_client.put_object(
            Bucket=bucket_name,
            Key="test-data/sample.csv",
            Body="id,name,email\n1,Test User,test@example.com",
        )

        yield bucket_name


def test_s3_operations_with_moto(s3_test_bucket, s3_client):
    """Test S3 operations using moto."""
    # List objects in bucket
    response = s3_client.list_objects_v2(Bucket=s3_test_bucket, Prefix="test-data/")

    # Verify the test file exists
    assert response["KeyCount"] == 1
    assert response["Contents"][0]["Key"] == "test-data/sample.csv"

    # Get the file content
    obj = s3_client.get_object(Bucket=s3_test_bucket, Key="test-data/sample.csv")
    content = obj["Body"].read().decode("utf-8")

    # Verify the content
    assert "id,name,email" in content
    assert "1,Test User,test@example.com" in content


def test_s3_service_integration(s3_test_bucket, s3_client):
    """Test S3Service integration with moto."""
    # Create S3Service
    s3_service = S3Service(region="us-west-2")

    # List objects in the bucket
    objects = s3_service.list_objects(bucket=s3_test_bucket, prefix="test-data/")

    # Verify the test file exists
    assert len(objects) == 1
    assert objects[0].key == "test-data/sample.csv"

    # Get the file content
    content = s3_service.get_object_content(
        bucket=s3_test_bucket,
        key="test-data/sample.csv",
    )

    # Verify the content
    assert "id,name,email" in content
    assert "1,Test User,test@example.com" in content

    # Test uploading a new file
    s3_service.put_object(
        bucket=s3_test_bucket,
        key="test-data/new-file.txt",
        content="This is a test file",
    )

    # Verify the upload
    new_content = s3_service.get_object_content(
        bucket=s3_test_bucket,
        key="test-data/new-file.txt",
    )
    assert new_content == "This is a test file"


@pytest.fixture
def entity_resolution_client(aws_credentials):
    """Create a mocked Entity Resolution client."""
    with mock_aws():
        # Create the client
        er_client = boto3.client("entityresolution", region_name="us-west-2")

        # Create a schema mapping
        schema_name = "test-schema"

        # Note: This is a simplified version as moto may not fully support Entity Resolution yet
        # In a real implementation, we would create the schema and workflow here

        yield er_client, schema_name


def test_entity_resolution_service_with_moto(entity_resolution_client, s3_test_bucket):
    """Test EntityResolutionService with moto and mocked client."""
    # Unpack the fixture
    client, mocks = entity_resolution_client

    # Create EntityResolutionService with the mocked client
    er_service = EntityResolutionService(region="us-west-2")

    # Set the client directly to use our mocked version
    er_service.client = client

    # Test creating a schema mapping
    schema_arn = er_service.create_schema_mapping(
        schema_name="test-schema",
        attributes=[
            {"name": "id", "type": "TEXT"},
            {"name": "name", "type": "TEXT"},
            {"name": "email", "type": "TEXT"},
        ],
    )

    # Verify the schema creation was called correctly
    assert mocks["create_schema"].called
    assert "arn:aws:entityresolution:" in schema_arn

    # Test listing schema mappings
    schemas = er_service.list_schema_mappings()

    # Verify the list schemas was called
    assert mocks["list_schemas"].called
    assert len(schemas) > 0
    assert schemas[0]["schemaName"] == "test-schema"

    # Test creating a matching workflow
    workflow_arn = er_service.create_matching_workflow(
        workflow_name="test-workflow",
        input_source_config={
            "s3SourceConfig": {
                "bucket": s3_test_bucket,
                "prefix": "test-data/",
            },
        },
        output_source_config={
            "s3OutputConfig": {
                "bucket": s3_test_bucket,
                "prefix": "output/",
            },
        },
        schema_arn=schema_arn,
    )

    # Verify workflow creation
    assert mocks["create_workflow"].called
    assert "arn:aws:entityresolution:" in workflow_arn

    # Test starting a matching job
    job_id = er_service.start_matching_job(
        workflow_arn=workflow_arn,
        input_source_config={
            "s3SourceConfig": {
                "bucket": s3_test_bucket,
                "prefix": "test-data/",
            },
        },
    )

    # Verify job start
    assert mocks["start_job"].called
    assert job_id == "test-job-id"

    # Test getting job status
    job_status = er_service.get_matching_job(job_id=job_id)

    # Verify job status retrieval
    assert mocks["get_job"].called
    assert job_status["jobStatus"] == "COMPLETED"


def test_s3_integration_with_settings(s3_test_bucket):
    """Test integration between S3 and Settings."""
    # Create settings with the test bucket
    settings = Settings(
        aws_region="us-west-2",
        s3={"bucket": s3_test_bucket, "prefix": "test-data/"},
    )

    # Create S3 client
    s3_client = boto3.client("s3", region_name=settings.aws_region)

    # List objects in the bucket using settings
    response = s3_client.list_objects_v2(
        Bucket=settings.s3.bucket,
        Prefix=settings.s3.prefix,
    )

    # Verify the test file exists
    assert response["KeyCount"] == 1
    assert response["Contents"][0]["Key"] == "test-data/sample.csv"


def test_settings_with_aws_services(s3_test_bucket):
    """Test Settings integration with multiple AWS services."""
    # Create comprehensive settings
    settings = Settings(
        aws_region="us-west-2",
        s3={
            "bucket": s3_test_bucket,
            "prefix": "test-data/",
            "output_prefix": "output/",
            "region": "us-west-2",
        },
        entity_resolution={
            "schema_name": "test-schema",
            "workflow_name": "test-workflow",
        },
    )

    # Test accessing settings
    assert settings.aws_region == "us-west-2"
    assert settings.s3.bucket == s3_test_bucket
    assert settings.s3.prefix == "test-data/"
    assert settings.entity_resolution.schema_name == "test-schema"

    # Create services with settings
    s3_service = S3Service(region=settings.aws_region)

    # Test operations with settings
    objects = s3_service.list_objects(
        bucket=settings.s3.bucket,
        prefix=settings.s3.prefix,
    )

    # Verify operations
    assert len(objects) == 1
    assert objects[0].key == "test-data/sample.csv"
