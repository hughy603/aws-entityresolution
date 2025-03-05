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
)
from aws_entity_resolution.services import S3Service, SnowflakeService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        aws_region="us-west-2",
        s3=S3Config(bucket="test-bucket", prefix="test-prefix/"),
        snowflake=SnowflakeConfig(
            account="test-account",
            username="test-user",
            password="test-password",
            role="test-role",
            warehouse="test-warehouse",
            source_database="test-source-db",
            source_schema="test-source-schema",
            source_table="test-source-table",
            target_database="test-target-db",
            target_schema="test-target-schema",
            target_table="test_target_table",
        ),
        entity_resolution=EntityResolutionConfig(
            workflow_name="test-workflow",
            schema_name="test-schema",
            entity_attributes=["id", "name", "email"],
        ),
    )


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
def mock_snowflake_service(mock_settings: Settings) -> SnowflakeService:
    """Create a mock SnowflakeService."""
    with patch.object(SnowflakeService, "connect"):
        service = SnowflakeService(mock_settings, use_target=True)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        service.connection = mock_conn
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
        patch.object(mock_snowflake_service, "execute_query") as mock_execute,
    ):
        # Set up the mock connection
        mock_connect.return_value = MagicMock()

        # Call the function
        create_target_table(mock_snowflake_service, mock_settings)

        # Verify the execute_query was called
        mock_execute.assert_called_once()


def test_create_target_table_error(
    mock_snowflake_service: SnowflakeService, mock_settings: Settings
) -> None:
    """Test error during target table creation."""
    # Patch the SnowflakeService class to avoid actual connections
    with (
        patch("snowflake.connector.connect") as mock_connect,
        patch.object(mock_snowflake_service, "connect") as mock_service_connect,
        patch.object(mock_snowflake_service, "execute_query") as mock_execute,
    ):
        # Set up the mock connection
        mock_connect.return_value = MagicMock()
        mock_service_connect.return_value = MagicMock()

        # Make the execute_query method raise an error
        mock_execute.side_effect = snowflake.connector.errors.ProgrammingError(
            "Table creation failed"
        )

        with pytest.raises(snowflake.connector.errors.ProgrammingError) as exc_info:
            create_target_table(mock_snowflake_service, mock_settings)

        assert "Table creation failed" in str(exc_info.value)


def test_load_matched_records_success(
    mock_snowflake_service: SnowflakeService,
    mock_settings: Settings,
    mock_matched_records: list[dict[str, Any]],
) -> None:
    """Test successful loading of matched records to Snowflake."""
    result = load_matched_records(mock_matched_records, mock_snowflake_service, mock_settings)

    assert result == 2

    # Verify records were inserted correctly
    mock_cursor = mock_snowflake_service.connection.cursor.return_value
    insert_sql = mock_cursor.executemany.call_args[0][0]
    assert "INSERT INTO" in insert_sql
    assert all(attr in insert_sql for attr in ["id", "name", "email", "MATCH_ID", "MATCH_SCORE"])

    mock_snowflake_service.connection.commit.assert_called_once()


def test_load_records_success(
    mock_settings: Settings,
    mock_matched_records: list[dict[str, Any]],
    mock_s3_service: S3Service,
    mock_snowflake_service: SnowflakeService,
) -> None:
    """Test successful record loading."""
    # Ensure S3 service returns valid data
    with patch.object(mock_s3_service, "read_object") as mock_read:
        mock_read.return_value = "\n".join([json.dumps(record) for record in mock_matched_records])

        # Mock the SnowflakeService to avoid actual connections
        with patch("aws_entity_resolution.loader.loader.SnowflakeService") as mock_sf_service_class:
            mock_sf_service_class.return_value.__enter__.return_value = mock_snowflake_service
            mock_sf_service_class.return_value.__exit__.return_value = None

            # Mock the create_target_table and load_matched_records functions
            with patch(
                "aws_entity_resolution.loader.loader.create_target_table"
            ) as mock_create_table:
                with patch("aws_entity_resolution.loader.loader.load_matched_records") as mock_load:
                    mock_load.return_value = 2  # Return 2 records loaded

                    result = load_records(
                        mock_settings,
                        "test-key",
                        s3_service=mock_s3_service,
                    )

                    # Verify the mocks were called
                    mock_create_table.assert_called_once()
                    mock_load.assert_called_once()

                    assert isinstance(result, LoadingResult)
                    assert result.status == "success"
                    assert result.records_loaded == 2
                    assert result.target_table == mock_settings.target_table


def test_load_records_no_data(mock_settings: Settings) -> None:
    """Test loading when no records are available."""
    with patch.object(S3Service, "read_object") as mock_read:
        mock_read.return_value = ""
        s3_service = S3Service(mock_settings)

        result = load_records(mock_settings, "test-key", s3_service=s3_service)

        assert isinstance(result, LoadingResult)
        assert result.status == "success"
        assert result.records_loaded == 0
        assert "No records to load" in result.error_message


def test_load_records_error(
    mock_settings: Settings,
    mock_matched_records: list[dict[str, Any]],
    mock_s3_service: S3Service,
    mock_snowflake_service: SnowflakeService,
) -> None:
    """Test error during record loading."""
    # Ensure S3 service returns valid data instead of raising NoCredentialsError
    with patch.object(
        mock_s3_service, "read_object", return_value=json.dumps(mock_matched_records)
    ):
        # Mock Snowflake connection to avoid connection errors
        with patch.object(SnowflakeService, "__enter__", return_value=mock_snowflake_service):
            with patch.object(SnowflakeService, "__exit__", return_value=None):
                with patch(
                    "aws_entity_resolution.loader.loader.create_target_table", return_value=None
                ):
                    # Configure the mock to raise an Error exception when load_matched_records is called
                    with patch(
                        "aws_entity_resolution.loader.loader.load_matched_records"
                    ) as mock_load:
                        mock_load.side_effect = snowflake.connector.errors.Error("Insert failed")

                        # The function should handle the exception and return an error status
                        result = load_records(
                            mock_settings,
                            "test-key",
                            s3_service=mock_s3_service,
                            snowflake_service=mock_snowflake_service,
                        )

                        assert result.status == "error"
                        assert "Insert failed" in result.error_message
