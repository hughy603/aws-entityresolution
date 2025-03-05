"""Tests for Lambda handlers."""

import time
from unittest.mock import MagicMock, patch

import pytest
from src.aws_entity_resolution.lambda_handlers import (
    check_status_handler,
    extract_handler,
    load_handler,
    process_handler,
)


@pytest.fixture
def mock_extract_result():
    """Create a mock extraction result."""
    result = MagicMock()
    result.status = "success"
    result.records_extracted = 100
    result.s3_bucket = "test-bucket"
    result.s3_key = "test-prefix/extracted.csv"
    return result


@pytest.fixture
def mock_process_result():
    """Create a mock process result."""
    result = MagicMock()
    result.status = "success"
    result.job_id = "test-job-id"
    return result


@pytest.fixture
def mock_load_result():
    """Create a mock load result."""
    result = MagicMock()
    result.status = "success"
    result.records_loaded = 50
    result.target_table = "test-target-table"
    return result


def test_extract_handler(mock_extract_result):
    """Test the extract handler."""
    with patch(
        "src.aws_entity_resolution.lambda_handlers.extract_data", return_value=mock_extract_result
    ):
        event = {}
        context = {}
        response = extract_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "success"
        assert response["body"]["records_extracted"] == 100
        assert response["body"]["s3_bucket"] == "test-bucket"
        assert response["body"]["s3_key"] == "test-prefix/extracted.csv"
        assert "timestamp" in response["body"]


def test_extract_handler_with_source_table_override(mock_extract_result):
    """Test the extract handler with source table override."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.get_settings") as mock_get_settings,
        patch(
            "src.aws_entity_resolution.lambda_handlers.extract_data",
            return_value=mock_extract_result,
        ),
    ):
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        event = {"source_table": "custom_table"}
        context = {}
        response = extract_handler(event, context)

        assert mock_settings.source_table == "custom_table"
        assert response["statusCode"] == 200
        assert response["body"]["status"] == "success"


def test_process_handler():
    """Test the process handler."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.S3Service") as mock_s3_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service_cls,
        patch("src.aws_entity_resolution.lambda_handlers.start_matching_job") as mock_start_job,
    ):
        # Setup mocks
        mock_s3_service = MagicMock()
        mock_s3_service_cls.return_value = mock_s3_service

        mock_er_service = MagicMock()
        mock_er_service_cls.return_value = mock_er_service

        mock_start_job.return_value = "test-job-id"

        # Test with input file from event
        event = {"body": {"s3_key": "test-input.csv"}}
        context = {}
        response = process_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "running"
        assert response["body"]["job_id"] == "test-job-id"
        assert "input_file" in response["body"]
        assert "output_prefix" in response["body"]

        # Verify the correct input file was used
        mock_start_job.assert_called_once()
        call_args = mock_start_job.call_args[0]
        assert call_args[1] == "test-input.csv"


def test_process_handler_find_latest():
    """Test the process handler when finding the latest input file."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.S3Service") as mock_s3_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.find_latest_input_path"
        ) as mock_find_latest,
        patch("src.aws_entity_resolution.lambda_handlers.start_matching_job") as mock_start_job,
    ):
        # Setup mocks
        mock_s3_service = MagicMock()
        mock_s3_service_cls.return_value = mock_s3_service

        mock_er_service = MagicMock()
        mock_er_service_cls.return_value = mock_er_service

        mock_find_latest.return_value = "latest-input.csv"
        mock_start_job.return_value = "test-job-id"

        # Test without input file in event
        event = {}
        context = {}
        response = process_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "running"
        assert response["body"]["job_id"] == "test-job-id"
        assert response["body"]["input_file"] == "latest-input.csv"

        # Verify the latest input file was found and used
        mock_find_latest.assert_called_once_with(mock_s3_service)
        mock_start_job.assert_called_once()
        call_args = mock_start_job.call_args[0]
        assert call_args[1] == "latest-input.csv"


def test_process_handler_no_input_found():
    """Test the process handler when no input file is found."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.S3Service") as mock_s3_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.find_latest_input_path"
        ) as mock_find_latest,
    ):
        # Setup mocks
        mock_s3_service = MagicMock()
        mock_s3_service_cls.return_value = mock_s3_service

        mock_er_service = MagicMock()
        mock_er_service_cls.return_value = mock_er_service

        mock_find_latest.return_value = None

        # Test with no input file available
        event = {}
        context = {}

        with pytest.raises(ValueError, match="No input data found"):
            process_handler(event, context)


def test_check_status_handler():
    """Test the check status handler."""
    with (
        patch(
            "src.aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.wait_for_matching_job"
        ) as mock_wait_for_job,
    ):
        # Setup mocks
        mock_er_service = MagicMock()
        mock_er_service_cls.return_value = mock_er_service

        mock_wait_for_job.return_value = {
            "status": "COMPLETED",
            "output_location": "test-output/",
            "statistics": {"recordsProcessed": 100, "recordsMatched": 50},
        }

        # Test with job ID in event
        event = {"body": {"job_id": "test-job-id"}}
        context = {}
        response = check_status_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "completed"
        assert response["body"]["is_complete"] is True
        assert response["body"]["job_id"] == "test-job-id"
        assert response["body"]["output_location"] == "test-output/"
        assert response["body"]["statistics"] == {"recordsProcessed": 100, "recordsMatched": 50}

        # Verify the correct job ID was used
        mock_wait_for_job.assert_called_once_with(mock_er_service, "test-job-id")


def test_check_status_handler_running():
    """Test the check status handler with a running job."""
    with (
        patch(
            "src.aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.wait_for_matching_job"
        ) as mock_wait_for_job,
    ):
        # Setup mocks
        mock_er_service = MagicMock()
        mock_er_service_cls.return_value = mock_er_service

        mock_wait_for_job.return_value = {
            "status": "RUNNING",
            "output_location": "",
            "statistics": {},
        }

        # Test with job ID in event
        event = {"body": {"job_id": "test-job-id"}}
        context = {}
        response = check_status_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "running"
        assert response["body"]["is_complete"] is False


def test_check_status_handler_no_job_id():
    """Test the check status handler with no job ID."""
    event = {}
    context = {}

    with pytest.raises(ValueError, match="No job_id provided"):
        check_status_handler(event, context)


def test_load_handler(mock_load_result):
    """Test the load handler."""
    with patch(
        "src.aws_entity_resolution.lambda_handlers.load_records", return_value=mock_load_result
    ):
        # Test with output location in event
        event = {"body": {"output_location": "test-output/"}}
        context = {}
        response = load_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "success"
        assert response["body"]["records_loaded"] == 50
        assert response["body"]["target_table"] == "test-target-table"
        assert "timestamp" in response["body"]


def test_load_handler_find_latest(mock_load_result):
    """Test the load handler when finding the latest output file."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.S3Service") as mock_s3_service_cls,
        patch(
            "src.aws_entity_resolution.lambda_handlers.load_records", return_value=mock_load_result
        ),
    ):
        # Setup mocks
        mock_s3_service = MagicMock()
        mock_s3_service.find_latest_path.return_value = "latest-output/matches.csv"
        mock_s3_service_cls.return_value = mock_s3_service

        # Test without output location in event
        event = {}
        context = {}
        response = load_handler(event, context)

        assert response["statusCode"] == 200
        assert response["body"]["status"] == "success"
        assert response["body"]["records_loaded"] == 50

        # Verify the latest output file was found and used
        mock_s3_service.find_latest_path.assert_called_once()


def test_load_handler_no_output_found():
    """Test the load handler when no output file is found."""
    with (
        patch("src.aws_entity_resolution.lambda_handlers.S3Service") as mock_s3_service_cls,
    ):
        # Setup mocks
        mock_s3_service = MagicMock()
        mock_s3_service.find_latest_path.return_value = None
        mock_s3_service_cls.return_value = mock_s3_service

        # Test with no output file available
        event = {}
        context = {}

        with pytest.raises(ValueError, match="No output data found"):
            load_handler(event, context)
