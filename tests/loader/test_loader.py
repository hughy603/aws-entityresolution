"""Tests for the AWS Entity Resolution loader module."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
import snowflake.connector

# Try to import from moto v5, fall back to individual mocks for older versions
try:
    from moto import mock_aws
except ImportError:
    from moto import mock_s3

    def mock_aws():
        return mock_s3()


from aws_entity_resolution.config import (
    EntityResolutionConfig,
    S3Config,
    Settings,
    SnowflakeConfig,
)
from aws_entity_resolution.loader.loader import (
    LoadingResult,
    create_target_table,
    load_matched_records,
    load_records,
    setup_snowflake_objects,
)
from aws_entity_resolution.services.s3 import S3Service
from aws_entity_resolution.services.snowflake import SnowflakeService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.target_table = "test_target"
    settings.aws_region = "us-east-1"

    # Mock S3 config
    s3_config = MagicMock()
    s3_config.bucket = "test-bucket"
    s3_config.prefix = "test-prefix/"
    settings.s3 = s3_config

    # Mock Snowflake target config
    snowflake_config = MagicMock()
    snowflake_config.storage_integration = "test_integration"
    settings.snowflake_target = snowflake_config

    return settings


@pytest.fixture
def mock_matched_records() -> list[dict[str, Any]]:
    """Create mock matched records for testing."""
    return [
        {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "matchId": "match-1",
            "matchScore": 0.95,
        },
        {
            "id": "2",
            "name": "Jane Smith",
            "email": "jane@example.com",
            "matchId": "match-2",
            "matchScore": 0.90,
        },
    ]


@pytest.fixture
def mock_snowflake_cursor():
    """Create a mock Snowflake cursor."""
    cursor = MagicMock()
    cursor.execute.return_value = MagicMock()
    cursor.execute.return_value.fetchone.return_value = [10]  # Mock 10 records affected
    return cursor


@pytest.fixture
def mock_snowflake_connection(mock_snowflake_cursor):
    """Create a mock Snowflake connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_snowflake_cursor
    return conn


@pytest.fixture
def mock_snowflake_service(mock_snowflake_connection):
    """Create a mock Snowflake service."""
    service = MagicMock(spec=SnowflakeService)
    service.connection = mock_snowflake_connection
    return service


@pytest.fixture
def mock_s3_service(
    mock_settings: Settings, mock_matched_records: list[dict[str, Any]], aws_credentials
) -> S3Service:
    """Create a mock S3Service."""
    with mock_aws():
        # Create S3 bucket
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket=mock_settings.s3.bucket)

        # Upload test data
        test_key = "test-key"
        test_data = "\n".join([json.dumps(record) for record in mock_matched_records])
        s3_client.put_object(Bucket=mock_settings.s3.bucket, Key=test_key, Body=test_data)

        # Create service with real boto3 that will use moto's mock
        service = S3Service(mock_settings)
        return service


def test_create_target_table_success(
    mock_snowflake_service: SnowflakeService, mock_settings: Settings
) -> None:
    """Test successful target table creation."""
    # Patch the SnowflakeService class to avoid actual connections
    with (
        patch("snowflake.connector.connect"),
        patch.object(mock_snowflake_service, "connect") as mock_connect,
        patch.object(mock_snowflake_service, "create_table") as mock_create_table,
    ):
        # Set up the mock connection
        mock_connect.return_value = MagicMock()
        mock_snowflake_service.connection = MagicMock()

        # Call the function
        create_target_table(mock_snowflake_service, mock_settings.target_table)

        # Verify the create_table was called
        mock_create_table.assert_called_once()


def test_create_target_table_error(
    mock_snowflake_service: SnowflakeService, mock_settings: Settings
) -> None:
    """Test error during target table creation."""
    # Patch the SnowflakeService class to avoid actual connections
    with (
        patch("snowflake.connector.connect") as mock_connect,
        patch.object(mock_snowflake_service, "connect") as mock_service_connect,
        patch.object(mock_snowflake_service, "create_table") as mock_create_table,
    ):
        # Set up the mock connection
        mock_connect.return_value = MagicMock()
        mock_service_connect.return_value = MagicMock()
        mock_snowflake_service.connection = MagicMock()

        # Make the create_table method raise an error
        mock_create_table.side_effect = snowflake.connector.errors.ProgrammingError(
            "Table creation failed"
        )

        with pytest.raises(snowflake.connector.errors.ProgrammingError) as exc_info:
            create_target_table(mock_snowflake_service, mock_settings.target_table)

        assert "Table creation failed" in str(exc_info.value)


def test_setup_snowflake_objects(mock_snowflake_service, mock_settings, tmp_path):
    """Test setting up Snowflake objects."""
    # Create a temporary setup.sql file
    setup_sql = """
    CREATE OR REPLACE FILE FORMAT test_format
        TYPE = 'JSON';
    """
    sql_path = tmp_path / "snowflake_setup.sql"
    sql_path.write_text(setup_sql)

    with patch("pathlib.Path.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = setup_sql

        setup_snowflake_objects(mock_snowflake_service, mock_settings)

        # Verify SQL execution
        cursor = mock_snowflake_service.connection.cursor()
        cursor.execute.assert_called()
        mock_snowflake_service.connection.commit.assert_called_once()


def test_load_matched_records_success(mock_snowflake_service, mock_settings):
    """Test successful loading of matched records."""
    s3_key = "test/output.json"

    result = load_matched_records(s3_key, mock_snowflake_service, mock_settings)

    # Verify SQL execution
    cursor = mock_snowflake_service.connection.cursor()

    # Check temp table creation - using parameterized query
    cursor.execute.assert_any_call(
        "CREATE TEMPORARY TABLE :temp_table LIKE :target_table",
        {"temp_table": "test_target_temp", "target_table": "test_target"},
    )

    # Check COPY command
    copy_call = any(
        "COPY INTO" in str(call) and "test_target_temp" in str(call)
        for call in cursor.execute.call_args_list
    )
    assert copy_call

    # Check MERGE command
    merge_call = any(
        "MERGE INTO" in str(call) and ":target_table" in str(call) and ":temp_table" in str(call)
        for call in cursor.execute.call_args_list
    )
    assert merge_call

    # Verify commit
    mock_snowflake_service.connection.commit.assert_called()

    # Check result
    assert result == 10  # From mock cursor fixture


def test_load_records_success(mock_settings, mock_snowflake_service):
    """Test successful record loading workflow."""
    s3_key = "test/output.json"

    with patch("aws_entity_resolution.loader.loader.setup_snowflake_objects") as mock_setup:
        with patch("aws_entity_resolution.loader.loader.load_matched_records") as mock_load:
            mock_load.return_value = 10

            result = load_records(
                mock_settings,
                s3_key,
                snowflake_service=mock_snowflake_service,
            )

            # Verify setup was called
            mock_setup.assert_called_once_with(mock_snowflake_service, mock_settings)

            # Verify load was called
            mock_load.assert_called_once_with(s3_key, mock_snowflake_service, mock_settings)

            # Check result
            assert isinstance(result, LoadingResult)
            assert result.status == "success"
            assert result.records_loaded == 10
            assert result.target_table == mock_settings.target_table
            assert result.execution_time is not None


def test_load_records_no_key_found(mock_settings, mock_snowflake_service):
    """Test loading when no S3 key is found."""
    with patch("aws_entity_resolution.services.s3.S3Service.find_latest_path") as mock_find:
        mock_find.return_value = None

        result = load_records(
            mock_settings,
            snowflake_service=mock_snowflake_service,
        )

        assert result.status == "error"
        assert "No matched records found" in result.error_message
        assert result.records_loaded == 0


def test_load_records_error(mock_settings, mock_snowflake_service):
    """Test loading when an error occurs."""
    s3_key = "test/output.json"

    with patch("aws_entity_resolution.loader.loader.setup_snowflake_objects") as mock_setup:
        mock_setup.side_effect = Exception("Test error")

        result = load_records(
            mock_settings,
            s3_key,
            snowflake_service=mock_snowflake_service,
        )

        assert result.status == "error"
        assert "Test error" in result.error_message
        assert result.records_loaded == 0
        assert result.execution_time is not None


def test_load_records_dry_run(mock_settings, mock_snowflake_service):
    """Test dry run mode."""
    result = load_records(
        mock_settings,
        "test/output.json",
        dry_run=True,
        snowflake_service=mock_snowflake_service,
    )

    assert result.status == "dry_run"
    assert result.records_loaded == 0
    assert result.execution_time is not None
