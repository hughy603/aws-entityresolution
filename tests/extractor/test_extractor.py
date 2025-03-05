"""Tests for the extractor module."""

from unittest.mock import MagicMock, patch

import boto3
import pytest
import snowflake.connector
from snowflake.connector import connect

from aws_entity_resolution.config import Settings
from aws_entity_resolution.extractor.extractor import (
    ExtractionResult,
    execute_query,
    extract_data,
    get_snowflake_connection,
    write_to_s3,
)


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Settings(
        aws_region="us-west-2",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        snowflake_source={
            "account": "test-account",
            "username": "test-user",
            "password": "test-password",
            "warehouse": "test-warehouse",
            "database": "test-db",
            "schema": "test-schema",
            "role": "ACCOUNTADMIN",
        },
        s3={
            "bucket": "test-bucket",
            "prefix": "test-prefix",
        },
        entity_resolution={
            "entity_attributes": ["id", "name", "email"],
        },
        source_table="test_source",
        target_table="test_target",
    )
    return settings


@pytest.fixture
def mock_snowflake_connection() -> MagicMock:
    """Create a mock Snowflake connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_get_snowflake_connection_success(mock_settings: Settings) -> None:
    """Test successful Snowflake connection."""
    with patch(
        "aws_entity_resolution.extractor.extractor.connect", return_value=MagicMock()
    ) as mock_connect:
        conn = get_snowflake_connection(mock_settings)
        assert conn is not None
        mock_connect.assert_called_once()


def test_get_snowflake_connection_error(mock_settings: Settings) -> None:
    """Test error handling for Snowflake connection."""
    with (
        patch(
            "aws_entity_resolution.extractor.extractor.connect",
            side_effect=snowflake.connector.errors.DatabaseError("Connection error"),
        ),
        pytest.raises(RuntimeError) as excinfo,
    ):
        get_snowflake_connection(mock_settings)
        assert "Connection error" in str(excinfo.value)


def test_execute_query_success(mock_snowflake_connection: MagicMock) -> None:
    """Test successful query execution."""
    # Set up the mock cursor
    mock_cursor = mock_snowflake_connection.cursor.return_value
    mock_cursor.description = [
        ("id", None, None, None, None, None, None),
        ("name", None, None, None, None, None, None),
    ]
    mock_cursor.fetchall.return_value = [(1, "Test"), (2, "Another")]

    # Execute the query
    result = execute_query(mock_snowflake_connection, "SELECT id, name FROM test")

    # Verify the result
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["name"] == "Test"
    assert result[1]["id"] == 2
    assert result[1]["name"] == "Another"


def test_execute_query_error(mock_snowflake_connection: MagicMock) -> None:
    """Test error handling for query execution."""
    # Make the cursor raise an error
    mock_cursor = mock_snowflake_connection.cursor.return_value
    mock_cursor.execute.side_effect = snowflake.connector.errors.ProgrammingError("SQL error")

    # Test that the error is properly raised
    with pytest.raises(RuntimeError) as excinfo:
        execute_query(mock_snowflake_connection, "SELECT * FROM nonexistent")
        assert "SQL error" in str(excinfo.value)


def test_write_to_s3_success(mock_settings: Settings) -> None:
    """Test successful S3 write."""
    records = [
        {"id": 1, "name": "Test"},
        {"id": 2, "name": "Another"},
    ]

    with patch("aws_entity_resolution.extractor.extractor.boto3.client") as mock_boto3_client:
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Mock the return value to include the full S3 path
        expected_s3_key = "test-prefix/entity_data.json"

        # Call the function
        with patch("aws_entity_resolution.extractor.extractor.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20230101_120000"
            s3_key = write_to_s3(records, mock_settings)

            # Verify the S3 key format
            assert mock_settings.s3.prefix in s3_key

            # In the actual implementation, we need to construct the full S3 URI
            s3_uri = f"s3://{mock_settings.s3.bucket}/{s3_key}"
            assert mock_settings.s3.bucket in s3_uri
            assert "entity_data.json" in s3_key

            mock_s3.put_object.assert_called_once()


def test_write_to_s3_error(mock_settings: Settings) -> None:
    """Test error handling for S3 write."""
    records = [
        {"id": 1, "name": "Test"},
        {"id": 2, "name": "Another"},
    ]

    with (
        patch("aws_entity_resolution.extractor.extractor.boto3.client") as mock_boto3_client,
        pytest.raises(RuntimeError) as excinfo,
    ):
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.put_object.side_effect = boto3.exceptions.Boto3Error("S3 error")

        write_to_s3(records, mock_settings)
        assert "S3 error" in str(excinfo.value)


def test_extract_data_success(
    mock_settings: Settings, mock_snowflake_connection: MagicMock
) -> None:
    """Test successful data extraction end-to-end."""
    # Create a mock SnowflakeService
    mock_snowflake_service = MagicMock()
    mock_snowflake_service.__enter__.return_value = mock_snowflake_service
    mock_records = [
        {"id": "1", "name": "Test User", "email": "test@example.com"},
        {"id": "2", "name": "Another User", "email": "another@example.com"},
    ]
    mock_snowflake_service.execute_query.return_value = mock_records

    # Create a mock S3Service
    mock_s3_service = MagicMock()
    mock_s3_service.write_object.return_value = (
        f"s3://{mock_settings.s3.bucket}/{mock_settings.s3.prefix}/test_data.csv"
    )

    # Call the function with our mocks
    result = extract_data(
        mock_settings, snowflake_service=mock_snowflake_service, s3_service=mock_s3_service
    )

    # Verify the result
    assert result.success is True
    assert mock_settings.s3.prefix in result.output_path
    assert result.record_count == 2
    assert result.error_message is None


def test_extract_data_snowflake_error(
    mock_settings: Settings, mock_snowflake_connection: MagicMock
) -> None:
    """Test handling of Snowflake query errors."""
    # Create a mock SnowflakeService
    mock_snowflake_service = MagicMock()
    mock_snowflake_service.__enter__.return_value = mock_snowflake_service

    # Make execute_query raise an error
    mock_snowflake_service.execute_query.side_effect = RuntimeError(
        "Failed to execute Snowflake query"
    )

    # Create a mock S3Service
    mock_s3_service = MagicMock()

    # Call the function with our mocks
    result = extract_data(
        mock_settings, snowflake_service=mock_snowflake_service, s3_service=mock_s3_service
    )

    # Verify the result
    assert result.success is False
    assert "Failed to execute Snowflake query" in result.error_message


def test_extract_data_s3_error(
    mock_settings: Settings, mock_snowflake_connection: MagicMock
) -> None:
    """Test handling of S3 write errors."""
    # Create a mock SnowflakeService
    mock_snowflake_service = MagicMock()
    mock_snowflake_service.__enter__.return_value = mock_snowflake_service

    # Mock the query execution
    mock_records = [
        {"id": "1", "name": "Test User", "email": "test@example.com"},
        {"id": "2", "name": "Another User", "email": "another@example.com"},
    ]
    mock_snowflake_service.execute_query.return_value = mock_records

    # Create a mock S3Service
    mock_s3_service = MagicMock()

    # Make S3 write raise an error
    mock_s3_service.write_object.side_effect = RuntimeError("Failed to write data to S3")

    # Call the function with our mocks
    result = extract_data(
        mock_settings, snowflake_service=mock_snowflake_service, s3_service=mock_s3_service
    )

    # Verify the result
    assert result.success is False
    assert "Failed to write data to S3" in result.error_message
