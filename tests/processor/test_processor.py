"""Tests for the AWS Entity Resolution processing module."""

from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from aws_entity_resolution.config import (
    Settings,
    SnowflakeConfig,
)
from aws_entity_resolution.processor.processor import (
    ProcessingResult,
    process_data,
    wait_for_matching_job,
)
from aws_entity_resolution.services import EntityResolutionService, S3Service


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Settings(
        aws_region="us-east-1", source_table="test_source", target_table="test_target"
    )

    # Set up S3 config
    settings.s3.bucket = "test-bucket"
    settings.s3.prefix = "test-prefix/"
    settings.s3.region = "us-east-1"

    # Set up Entity Resolution config
    settings.entity_resolution.workflow_name = "test-workflow"
    settings.entity_resolution.schema_name = "test-schema"
    settings.entity_resolution.entity_attributes = ["id", "name", "email"]

    # Set up minimal Snowflake configs
    snowflake_config = SnowflakeConfig(
        account="test-account",
        username="test-user",
        password="test-password",
        warehouse="test-warehouse",
        database="test-database",
        schema="test-schema",
    )
    settings.snowflake_source = snowflake_config
    settings.snowflake_target = snowflake_config

    return settings


@pytest.fixture
def mock_s3_list_response() -> dict[str, Any]:
    """Create a mock S3 list objects response."""
    return {
        "CommonPrefixes": [
            {"Prefix": "test-prefix/20240101_120000/"},
            {"Prefix": "test-prefix/20240101_110000/"},
        ],
        "Contents": [
            {"Key": "test-prefix/20240101_120000/entity_data.json"},
            {"Key": "test-prefix/20240101_120000/metadata.json"},
        ],
    }


@pytest.fixture
def mock_matching_job_response() -> dict[str, Any]:
    """Create a mock Entity Resolution matching job response."""
    return {
        "jobId": "test-job-id",
        "jobStatus": "SUCCEEDED",
        "outputSourceConfig": {"s3OutputConfig": {"key": "test-prefix/output/20240101_120000/"}},
        "statistics": {"inputRecordCount": 100, "matchedRecordCount": 80},
    }


def test_s3_service_find_latest_path_success(
    mock_settings: Settings, mock_s3_list_response: dict[str, Any]
) -> None:
    """Test successful finding of latest input path."""
    with patch("boto3.client") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = mock_s3_list_response

        s3_service = S3Service(mock_settings)
        result = s3_service.find_latest_path()

        assert result == "test-prefix/20240101_120000/entity_data.json"
        mock_s3.list_objects_v2.assert_called()


def test_s3_service_find_latest_path_no_data(mock_settings: Settings) -> None:
    """Test finding latest input path with no data."""
    with patch("boto3.client") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {}

        s3_service = S3Service(mock_settings)
        result = s3_service.find_latest_path()

        assert result is None


def test_s3_service_find_latest_path_s3_error(mock_settings: Settings) -> None:
    """Test S3 error handling when finding latest input path."""
    with (
        patch("boto3.client") as mock_boto3,
        patch("src.aws_entity_resolution.utils.handle_exceptions", lambda x: lambda f: f),
    ):
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The bucket does not exist"}},
            "ListObjectsV2",
        )

        with pytest.raises(ClientError) as exc_info:
            s3_service = S3Service(mock_settings)
            s3_service.find_latest_path()

        assert "NoSuchBucket" in str(exc_info.value)


def test_start_matching_job_success(
    mock_settings: Settings, mock_matching_job_response: dict[str, Any]
) -> None:
    """Test successful starting of matching job."""
    with patch("boto3.client") as mock_boto3:
        mock_er = MagicMock()
        mock_boto3.return_value = mock_er
        mock_er.start_matching_job.return_value = mock_matching_job_response

        er_service = EntityResolutionService(mock_settings)
        job_id = er_service.start_matching_job("test-input.json", "output/")

        assert job_id == "test-job-id"
        mock_er.start_matching_job.assert_called_once()


def test_start_matching_job_error(mock_settings: Settings) -> None:
    """Test error handling when starting matching job."""
    with (
        patch("boto3.client") as mock_boto3,
        patch("src.aws_entity_resolution.utils.handle_exceptions", lambda x: lambda f: f),
    ):
        mock_er = MagicMock()
        mock_boto3.return_value = mock_er
        mock_er.start_matching_job.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid workflow"}},
            "StartMatchingJob",
        )

        with pytest.raises(ClientError) as exc_info:
            er_service = EntityResolutionService(mock_settings)
            er_service.start_matching_job("test-input.json", "output/")

        assert "ValidationException" in str(exc_info.value)


def test_wait_for_matching_job_success(
    mock_settings: Settings, mock_matching_job_response: dict[str, Any]
) -> None:
    """Test successful waiting for matching job."""
    # Use EntityResolutionService directly instead of Settings
    mock_er_service = MagicMock()
    mock_er_service.get_job_status.return_value = {
        "status": "SUCCEEDED",
        "output_location": mock_matching_job_response["outputSourceConfig"]["s3OutputConfig"][
            "key"
        ],
        "statistics": mock_matching_job_response["statistics"],
        "errors": [],
    }

    result = wait_for_matching_job(mock_er_service, "test-job-id")

    assert result["status"] == "SUCCEEDED"
    assert result["statistics"] == mock_matching_job_response["statistics"]
    mock_er_service.get_job_status.assert_called_once_with("test-job-id")


def test_wait_for_matching_job_failure(mock_settings: Settings) -> None:
    """Test handling of failed matching job."""
    # Use EntityResolutionService directly instead of Settings
    mock_er_service = MagicMock()
    mock_er_service.get_job_status.return_value = {
        "status": "FAILED",
        "output_location": "",
        "statistics": {},
        "errors": "Processing error occurred",
    }

    with pytest.raises(RuntimeError) as exc_info:
        wait_for_matching_job(mock_er_service, "test-job-id")

    assert "Matching job failed" in str(exc_info.value)
    mock_er_service.get_job_status.assert_called_once_with("test-job-id")


def test_process_data_success(
    mock_settings: Settings,
    mock_s3_list_response: dict[str, Any],
    mock_matching_job_response: dict[str, Any],
) -> None:
    """Test successful end-to-end data processing."""
    with patch("boto3.client") as mock_boto3:
        # Mock both S3 and Entity Resolution clients
        def get_mock_client(service: str, region_name: str) -> MagicMock:
            if service == "s3":
                mock_s3 = MagicMock()
                mock_s3.list_objects_v2.return_value = mock_s3_list_response
                return mock_s3
            # entityresolution
            mock_er = MagicMock()
            mock_er.start_matching_job.return_value = mock_matching_job_response
            mock_er.get_matching_job.return_value = mock_matching_job_response
            return mock_er

        mock_boto3.side_effect = get_mock_client

        result = process_data(mock_settings)

        assert isinstance(result, ProcessingResult)
        assert result.status == "success"
        assert result.input_records == 100
        assert result.matched_records == 80
        assert result.s3_bucket == mock_settings.s3.bucket


def test_process_data_no_input(mock_settings: Settings) -> None:
    """Test processing with no input data."""
    # Use mock_aws instead of mock_s3
    with mock_aws():
        # Create empty S3 bucket to simulate no data
        s3_client = boto3.client(
            "s3",
            region_name="us-east-1",  # Use us-east-1 for moto
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )

        # For us-east-1, don't specify LocationConstraint
        if s3_client.meta.region_name == "us-east-1":
            s3_client.create_bucket(Bucket="test-bucket")
        else:
            s3_client.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": s3_client.meta.region_name},
            )

        # We'll let the real S3Service be created but it will use moto's mocked S3
        with pytest.raises(ValueError) as exc_info:
            process_data(mock_settings)

        assert "No input data found" in str(exc_info.value)


def test_process_data_matching_error(
    mock_settings: Settings, mock_s3_list_response: dict[str, Any]
) -> None:
    """Test processing with matching job error."""
    # Use mock_aws instead of mock_s3
    with mock_aws():
        # Create S3 bucket and add a test file
        s3_client = boto3.client(
            "s3",
            region_name="us-east-1",  # Use us-east-1 for moto
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )

        # For us-east-1, don't specify LocationConstraint
        if s3_client.meta.region_name == "us-east-1":
            s3_client.create_bucket(Bucket="test-bucket")
        else:
            s3_client.create_bucket(
                Bucket="test-bucket",
                CreateBucketConfiguration={"LocationConstraint": s3_client.meta.region_name},
            )

        # Add a test entity file
        s3_client.put_object(
            Bucket="test-bucket",
            Key="test-prefix/20240101_120000/entity_data.json",
            Body='{"entities": [{"id": "1", "name": "Test"}]}',
        )

        # Create a directory structure that will be found by find_latest_path
        for prefix in ["test-prefix/20240101_120000/", "test-prefix/20240101_110000/"]:
            s3_client.put_object(Bucket="test-bucket", Key=f"{prefix.rstrip('/')}/", Body="")

        # Mock EntityResolution service since it's not supported by moto
        error_message = "Error starting job: Invalid workflow"

        # We need to patch at a lower level to avoid the actual API call
        with patch(
            "src.aws_entity_resolution.services.EntityResolutionService.start_matching_job"
        ) as mock_start_job:
            mock_start_job.side_effect = RuntimeError(error_message)

            with pytest.raises(RuntimeError) as exc_info:
                process_data(mock_settings)

            assert error_message in str(exc_info.value)
            mock_start_job.assert_called_once()
