"""Tests for aws_utils.py module."""

import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from src.aws_entity_resolution.aws_utils import (
    find_latest_s3_path,
    get_entity_resolution_job_status,
    list_s3_objects,
    start_entity_resolution_job,
)
from src.aws_entity_resolution.config import Settings


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
def prepare_s3_test_data(s3_mock):
    """Create test data in the mocked S3 bucket."""
    bucket_name = "test-bucket"

    # Clear any existing objects
    objects = s3_mock.list_objects_v2(Bucket=bucket_name).get("Contents", [])
    if objects:
        delete_keys = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
        s3_mock.delete_objects(Bucket=bucket_name, Delete=delete_keys)

    # Create some test objects with date prefixes
    s3_mock.put_object(Bucket=bucket_name, Key="test-prefix/2023-01-01/file1.csv", Body="test data")
    s3_mock.put_object(
        Bucket=bucket_name, Key="test-prefix/2023-01-01/file2.json", Body="test data"
    )
    s3_mock.put_object(Bucket=bucket_name, Key="test-prefix/2023-02-01/file1.csv", Body="test data")
    s3_mock.put_object(
        Bucket=bucket_name, Key="test-prefix/2023-02-01/file2.json", Body="test data"
    )

    return bucket_name


def test_list_s3_objects(prepare_s3_test_data, s3_mock):
    """Test listing S3 objects."""
    result = list_s3_objects("test-bucket", "test-prefix/", "us-west-2")

    # Should return prefixes for the two date directories
    assert len(result["prefixes"]) == 2
    assert "test-prefix/2023-01-01/" in result["prefixes"]
    assert "test-prefix/2023-02-01/" in result["prefixes"]

    # The current implementation doesn't include the prefix itself in the files list
    assert len(result["files"]) == 0

    # Test with a specific prefix
    result = list_s3_objects("test-bucket", "test-prefix/2023-01-01/", "us-west-2", delimiter="")
    assert len(result["files"]) == 2
    assert "test-prefix/2023-01-01/file1.csv" in result["files"]
    assert "test-prefix/2023-01-01/file2.json" in result["files"]


def test_list_s3_objects_error():
    """Test error handling when listing S3 objects."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The bucket does not exist"}},
            "ListObjectsV2",
        )

        # The handle_exceptions decorator logs the error but still raises it
        with pytest.raises(ClientError):
            list_s3_objects("non-existent-bucket", "prefix/", "us-west-2")


def test_find_latest_s3_path(prepare_s3_test_data, mock_aws_settings):
    """Test finding the latest S3 path."""
    # The latest directory is 2023-02-01
    result = find_latest_s3_path(mock_aws_settings, file_pattern=".json")
    assert result == "test-prefix/2023-02-01/file2.json"

    # Test with a different file pattern
    result = find_latest_s3_path(mock_aws_settings, file_pattern=".csv")
    assert result == "test-prefix/2023-02-01/file1.csv"


def test_find_latest_s3_path_no_prefixes(mock_aws_settings):
    """Test finding the latest S3 path when no prefixes exist."""
    with patch("src.aws_entity_resolution.aws_utils.list_s3_objects") as mock_list:
        mock_list.return_value = {"prefixes": [], "files": []}
        result = find_latest_s3_path(mock_aws_settings)
        assert result is None


def test_find_latest_s3_path_no_matching_files(mock_aws_settings):
    """Test finding the latest S3 path when no matching files exist."""
    with patch("src.aws_entity_resolution.aws_utils.list_s3_objects") as mock_list:
        # First call returns prefixes
        mock_list.side_effect = [
            {"prefixes": ["test-prefix/2023-02-01/"], "files": []},
            {"prefixes": [], "files": ["test-prefix/2023-02-01/file1.txt"]},
        ]

        # No .json files in the latest directory
        result = find_latest_s3_path(mock_aws_settings, file_pattern=".json")
        assert result is None


def test_start_entity_resolution_job(mock_aws_settings, mock_entity_resolution_client):
    """Test starting an Entity Resolution job."""
    job_id = start_entity_resolution_job(mock_aws_settings, "test-input.csv", "test-output/")

    assert job_id == "test-job-id"
    mock_entity_resolution_client.start_matching_job.assert_called_once_with(
        workflowName="test-workflow",
        inputSourceConfig={"s3SourceConfig": {"bucket": "test-bucket", "key": "test-input.csv"}},
        outputSourceConfig={
            "s3OutputConfig": {
                "bucket": "test-bucket",
                "key": "test-output/",
                "applyNormalization": True,
            }
        },
    )


def test_start_entity_resolution_job_error(mock_aws_settings):
    """Test error handling when starting an Entity Resolution job."""
    # We need to patch the boto3 client directly for the error test
    with patch("boto3.client") as mock_client:
        mock_er = MagicMock()
        mock_client.return_value = mock_er
        mock_er.start_matching_job.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid workflow name"}},
            "StartMatchingJob",
        )

        # Should raise the exception which is caught by the handle_exceptions decorator
        with pytest.raises(ClientError):
            start_entity_resolution_job(mock_aws_settings, "test-input.csv", "test-output/")


def test_get_entity_resolution_job_status(mock_aws_settings, mock_entity_resolution_client):
    """Test getting Entity Resolution job status."""
    status = get_entity_resolution_job_status(mock_aws_settings, "test-job-id")

    assert status["status"] == "COMPLETED"
    assert status["output_location"] == "test-output/"
    assert status["statistics"] == {"recordsProcessed": 100, "recordsMatched": 50}
    assert status["errors"] == []


def test_get_entity_resolution_job_status_error(mock_aws_settings):
    """Test error handling when getting Entity Resolution job status."""
    # We need to patch the boto3 client directly for the error test
    with patch("boto3.client") as mock_client:
        mock_er = MagicMock()
        mock_client.return_value = mock_er
        mock_er.get_matching_job.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Job not found"}},
            "GetMatchingJob",
        )

        # Should raise the exception which is caught by the handle_exceptions decorator
        with pytest.raises(ClientError):
            get_entity_resolution_job_status(mock_aws_settings, "non-existent-job")
