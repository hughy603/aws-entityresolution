"""Basic AWS tests to demonstrate moto usage with the latest mock_aws decorator.

This file demonstrates how to use moto with the latest mock_aws syntax for supported
services, while also showing how to mock unsupported services like Entity Resolution.
"""

from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from aws_entity_resolution.config import Settings
from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.s3 import S3Service


# Example 1: Basic mock_aws decorator usage
@mock_aws
def test_s3_basic_operations():
    """Test basic S3 operations using the moto mock_aws decorator."""
    # Create a client
    s3 = boto3.client("s3", region_name="us-west-2")

    # Create a bucket
    s3.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Add an object
    s3.put_object(
        Bucket="test-bucket",
        Key="test/hello.txt",
        Body="Hello, World!",
    )

    # List objects
    response = s3.list_objects_v2(Bucket="test-bucket", Prefix="test/")

    # Verify
    assert "Contents" in response
    assert len(response["Contents"]) == 1
    assert response["Contents"][0]["Key"] == "test/hello.txt"


# Example 2: Using fixture for mock_aws
def test_s3_with_fixture(aws_mock):
    """Test S3 operations using the aws_mock fixture."""
    # Create a client
    s3 = boto3.client("s3", region_name="us-west-2")

    # Create a bucket
    s3.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Add an object
    s3.put_object(
        Bucket="test-bucket",
        Key="test/hello.txt",
        Body="Hello, World!",
    )

    # List objects
    response = s3.list_objects_v2(Bucket="test-bucket", Prefix="test/")

    # Verify
    assert "Contents" in response
    assert len(response["Contents"]) == 1
    assert response["Contents"][0]["Key"] == "test/hello.txt"


# Example 3: Mocking Entity Resolution (not supported by moto)
def test_entity_resolution_mocking():
    """Test how to mock Entity Resolution which is not supported by moto."""
    # Mock the log_event function to prevent errors
    with (
        patch("boto3.client") as mock_client,
        patch("aws_entity_resolution.services.entity_resolution.log_event") as mock_log_event,
    ):
        # Create a mock ER client
        mock_er = MagicMock()
        mock_client.return_value = mock_er

        # Set up mock responses
        mock_er.start_matching_job.return_value = {"jobId": "test-job-id"}
        mock_er.get_matching_job.return_value = {
            "jobId": "test-job-id",
            "jobStatus": "COMPLETED",
            "statistics": {"recordsProcessed": 100, "recordsMatched": 50},
        }

        # Create settings
        settings = MagicMock(spec=Settings)
        settings.aws_region = "us-west-2"
        settings.entity_resolution = MagicMock()
        settings.entity_resolution.workflow_name = "test-workflow"

        # Create the service
        er_service = EntityResolutionService(settings)

        # Test the service
        job_id = er_service.start_matching_job("test-input.csv", "test-output/")
        status = er_service.get_job_status(job_id)

        # Verify
        assert job_id == "test-job-id"
        assert status["jobStatus"] == "COMPLETED"
        assert status["statistics"]["recordsMatched"] == 50

        # Verify log_event was called
        mock_log_event.assert_called()


# Example 4: Combining moto and manual mocking
@mock_aws
def test_hybrid_mocking_approach():
    """Test combining moto for supported services with manual mocks for unsupported ones."""
    # Set up S3 using moto (supported)
    s3 = boto3.client("s3", region_name="us-west-2")
    bucket_name = "test-bucket"
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    s3.put_object(Bucket=bucket_name, Key="test-prefix/input.csv", Body="test data")

    # Mock the log_event function properly in both services
    with (
        patch("aws_entity_resolution.services.s3.log_event") as mock_s3_log,
        patch("aws_entity_resolution.services.entity_resolution.log_event") as mock_er_log,
        patch("boto3.client") as mock_client,
    ):
        # Create a mock ER client
        mock_er = MagicMock()
        # Only patch entityresolution, let other boto3.client calls work normally
        mock_client.side_effect = (
            lambda service, **kwargs: mock_er
            if service == "entityresolution"
            else boto3._get_default_session().client(service, **kwargs)
        )

        # Set up mock responses
        mock_er.start_matching_job.return_value = {"jobId": "test-job-id"}
        mock_er.get_matching_job.return_value = {
            "jobId": "test-job-id",
            "jobStatus": "COMPLETED",
            "statistics": {"recordsProcessed": 100, "recordsMatched": 50},
            "outputSourceConfig": {
                "s3OutputConfig": {
                    "key": "test-output/",
                },
            },
            "errors": [],
        }

        # Create settings
        settings = MagicMock(spec=Settings)
        settings.aws_region = "us-west-2"
        settings.s3 = MagicMock()
        settings.s3.bucket = bucket_name
        settings.s3.prefix = "test-prefix/"
        settings.s3.region = "us-west-2"
        settings.entity_resolution = MagicMock()
        settings.entity_resolution.workflow_name = "test-workflow"

        # Test using both S3 and EntityResolution
        s3_service = S3Service(settings)
        er_service = EntityResolutionService(settings)

        # Verify S3 works with moto
        files = s3_service.list_objects("test-prefix/")
        assert "test-prefix/input.csv" in files["files"]
        assert mock_s3_log.called

        # Verify Entity Resolution works with patch
        job_id = er_service.start_matching_job("test-input.csv", "test-prefix/output/")
        assert job_id == "test-job-id"

        # Call get_job_status to trigger log_event
        status = er_service.get_job_status(job_id)
        assert status["jobStatus"] == "COMPLETED"
        assert mock_er_log.called


# Example 5: Using pytest parametrize with mock_aws
@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("file1.txt", "Content 1"),
        ("file2.txt", "Content 2"),
        ("file3.txt", "Content 3"),
    ],
)
@mock_aws
def test_parametrized_s3_test(file_name, content):
    """Test using pytest parametrize with mock_aws."""
    # Set up S3
    s3 = boto3.client("s3", region_name="us-west-2")
    bucket_name = "test-bucket"
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Add the test file
    s3.put_object(
        Bucket=bucket_name,
        Key=f"test/{file_name}",
        Body=content,
    )

    # Verify the file was added
    response = s3.get_object(Bucket=bucket_name, Key=f"test/{file_name}")
    retrieved_content = response["Body"].read().decode("utf-8")

    assert retrieved_content == content


def test_s3_operations(s3_client):
    """Test that S3 mocking is working properly."""
    # Create a test bucket
    bucket_name = "test-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Check bucket exists
    response = s3_client.list_buckets()
    buckets = [bucket["Name"] for bucket in response["Buckets"]]
    assert bucket_name in buckets

    # Put an object
    s3_client.put_object(Bucket=bucket_name, Key="test-key", Body="test-content")

    # Check object exists
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    assert "Contents" in response
    assert response["Contents"][0]["Key"] == "test-key"
