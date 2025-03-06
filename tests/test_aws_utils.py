"""Tests for AWS service classes.

This file tests the service classes that interact with AWS.
"""

from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from aws_entity_resolution.config import Settings
from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.s3 import S3Service


@pytest.fixture
def mock_aws_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.aws_region = "us-west-2"
    settings.s3 = MagicMock()
    settings.s3.bucket = "test-bucket"
    settings.s3.prefix = "test-prefix/"
    settings.s3.region = "us-west-2"
    settings.entity_resolution = MagicMock()
    settings.entity_resolution.workflow_name = "test-workflow"
    return settings


@pytest.fixture
def prepare_s3_test_data(aws_mock):
    """Create test data in the mocked S3 bucket."""
    # Using the aws_mock fixture which uses the mock_aws decorator
    s3 = boto3.client("s3", region_name="us-west-2")
    bucket_name = "test-bucket"

    # Create the bucket
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Clear any existing objects
    try:
        objects = s3.list_objects_v2(Bucket=bucket_name).get("Contents", [])
        if objects:
            delete_keys = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
            s3.delete_objects(Bucket=bucket_name, Delete=delete_keys)
    except ClientError:
        # Bucket might not exist yet
        pass

    # Create some test objects with date prefixes
    s3.put_object(Bucket=bucket_name, Key="test-prefix/2023-01-01/file1.csv", Body="test data")
    s3.put_object(
        Bucket=bucket_name,
        Key="test-prefix/2023-01-01/file2.json",
        Body="test data",
    )
    s3.put_object(Bucket=bucket_name, Key="test-prefix/2023-02-01/file1.csv", Body="test data")
    s3.put_object(
        Bucket=bucket_name,
        Key="test-prefix/2023-02-01/file2.json",
        Body="test data",
    )

    return bucket_name


# The aws_mock fixture is automatically used here through prepare_s3_test_data
def test_s3service_list_objects(prepare_s3_test_data, mock_aws_settings):
    """Test listing S3 objects using S3Service directly."""
    # Also patch the log_event function to prevent errors
    with patch("aws_entity_resolution.services.s3.log_event"):
        s3_service = S3Service(mock_aws_settings)

        result = s3_service.list_objects("test-prefix/")

        # Should return prefixes for the two date directories
        assert len(result["prefixes"]) == 2
        assert "test-prefix/2023-01-01/" in result["prefixes"]
        assert "test-prefix/2023-02-01/" in result["prefixes"]

        # The current implementation doesn't include the prefix itself in the files list
        assert len(result["files"]) == 0

        # Test with a specific prefix
        result = s3_service.list_objects("test-prefix/2023-01-01/", delimiter="")
        assert len(result["files"]) == 2
        assert "test-prefix/2023-01-01/file1.csv" in result["files"]
        assert "test-prefix/2023-01-01/file2.json" in result["files"]


def test_s3service_list_objects_error(mock_aws_settings):
    """Test error handling when listing S3 objects with S3Service directly."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The bucket does not exist"}},
            "ListObjectsV2",
        )

        s3_service = S3Service(mock_aws_settings)

        # The handle_exceptions decorator logs the error but still raises it
        with pytest.raises(ClientError):
            s3_service.list_objects("prefix/")


def test_s3service_find_latest_path(prepare_s3_test_data, mock_aws_settings):
    """Test finding the latest S3 path with S3Service directly."""
    # Also patch the log_event function to prevent errors
    with patch("aws_entity_resolution.services.s3.log_event"):
        s3_service = S3Service(mock_aws_settings)

        # The latest directory is 2023-02-01
        result = s3_service.find_latest_path(mock_aws_settings.s3.prefix, file_pattern=".json")
        assert result == "test-prefix/2023-02-01/file2.json"

        # Test with a different file pattern
        result = s3_service.find_latest_path(mock_aws_settings.s3.prefix, file_pattern=".csv")
        assert result == "test-prefix/2023-02-01/file1.csv"


def test_s3service_find_latest_path_no_prefixes(mock_aws_settings):
    """Test finding the latest S3 path when no prefixes exist with S3Service directly."""
    with patch("aws_entity_resolution.services.s3.S3Service.list_objects") as mock_list:
        mock_list.return_value = {"prefixes": [], "files": []}

        s3_service = S3Service(mock_aws_settings)
        result = s3_service.find_latest_path()
        assert result is None


def test_s3service_find_latest_path_no_matching_files(mock_aws_settings):
    """Test finding the latest S3 path when no matching files exist with S3Service directly."""
    with (
        patch("aws_entity_resolution.services.s3.S3Service.list_objects") as mock_list,
        patch("aws_entity_resolution.services.s3.log_event"),
    ):
        # First call returns prefixes, second call returns files
        mock_list.side_effect = [
            {"prefixes": ["test-prefix/2023-02-01/"], "files": []},
            {"prefixes": [], "files": ["test-prefix/2023-02-01/file1.txt"]},
        ]

        s3_service = S3Service(mock_aws_settings)
        # No .json files in the latest directory
        result = s3_service.find_latest_path(file_pattern=".json")
        assert result is None


def test_entityresolutionservice_start_matching_job(
    mock_aws_settings,
    mock_entity_resolution_client,
):
    """Test starting an Entity Resolution job with EntityResolutionService directly."""
    # Also patch the log_event function
    with patch("aws_entity_resolution.services.entity_resolution.log_event"):
        er_service = EntityResolutionService(mock_aws_settings)
        job_id = er_service.start_matching_job("test-input.csv", "test-output/")

        assert job_id == "test-job-id"
        mock_entity_resolution_client.start_matching_job.assert_called_once_with(
            workflowName="test-workflow",
            inputSourceConfig={"s3SourceConfig": {"source": "test-input.csv"}},
            outputSourceConfig={
                "s3OutputConfig": {
                    "destination": "test-output/",
                },
            },
        )


def test_entityresolutionservice_start_matching_job_error(mock_aws_settings):
    """Test error handling when starting an Entity Resolution job with EntityResolutionService directly."""
    with (
        patch("boto3.client") as mock_client,
        patch("aws_entity_resolution.services.entity_resolution.log_event"),
    ):
        mock_er = MagicMock()
        mock_client.return_value = mock_er
        mock_er.start_matching_job.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationException",
                    "Message": "Workflow not found",
                },
            },
            "StartMatchingJob",
        )

        er_service = EntityResolutionService(mock_aws_settings)

        # The handle_exceptions decorator logs the error but still raises it
        with pytest.raises(ClientError):
            er_service.start_matching_job("test-input.csv", "test-output/")


def test_entityresolutionservice_get_job_status(mock_aws_settings, mock_entity_resolution_client):
    """Test getting Entity Resolution job status with EntityResolutionService directly."""
    with patch("aws_entity_resolution.services.entity_resolution.log_event"):
        er_service = EntityResolutionService(mock_aws_settings)
        status = er_service.get_job_status("test-job-id")

        assert status["status"] == "COMPLETED"
        # Check the output location from the outputSourceConfig
        assert "outputSourceConfig" in status
        assert "s3OutputConfig" in status["outputSourceConfig"]
        assert status["outputSourceConfig"]["s3OutputConfig"]["key"] == "test-output/"
        assert status["statistics"] == {"recordsProcessed": 100, "recordsMatched": 50}
        assert status["errors"] == []
        mock_entity_resolution_client.get_matching_job.assert_called_once_with(jobId="test-job-id")


def test_entityresolutionservice_get_job_status_error(mock_aws_settings):
    """Test error handling when getting Entity Resolution job status with EntityResolutionService directly."""
    with (
        patch("boto3.client") as mock_client,
        patch("aws_entity_resolution.services.entity_resolution.log_event"),
    ):
        mock_er = MagicMock()
        mock_client.return_value = mock_er
        mock_er.get_matching_job.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Job not found",
                },
            },
            "GetMatchingJob",
        )

        er_service = EntityResolutionService(mock_aws_settings)

        # The handle_exceptions decorator logs the error but still raises it
        with pytest.raises(ClientError):
            er_service.get_job_status("non-existent-job-id")
