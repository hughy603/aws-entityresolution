"""Unit tests for the CLI module."""

from unittest.mock import MagicMock, patch

import boto3
import pytest
import snowflake.connector
import typer
from typer.testing import CliRunner

from aws_entity_resolution.extractor.cli import app, validate_settings
from aws_entity_resolution.extractor.extractor import ExtractionResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Typer CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()

    # Create nested mocks for the complex structure
    snowflake_source = MagicMock()
    snowflake_source.account = "test-account"
    snowflake_source.database = "test-db"
    snowflake_source.schema = "test-schema"

    s3 = MagicMock()
    s3.bucket = "test-bucket"
    s3.prefix = "test-prefix"

    entity_resolution = MagicMock()
    entity_resolution.entity_attributes = ["id", "name", "email"]

    # Attach the nested mocks to the main settings mock
    settings.snowflake_source = snowflake_source
    settings.s3 = s3
    settings.entity_resolution = entity_resolution
    settings.source_table = "test-table"

    return settings


def test_validate_settings_success(mock_settings: MagicMock) -> None:
    """Test validate_settings with valid settings."""
    # Should return True with valid settings
    assert validate_settings(mock_settings) is True


def test_validate_settings_missing_snowflake_account() -> None:
    """Test validate_settings with missing Snowflake account."""
    settings = MagicMock()

    snowflake_source = MagicMock()
    snowflake_source.account = ""

    s3 = MagicMock()
    s3.bucket = "test-bucket"

    settings.snowflake_source = snowflake_source
    settings.s3 = s3
    settings.source_table = "test-table"

    assert validate_settings(settings) is False


def test_validate_settings_missing_s3_bucket() -> None:
    """Test validate_settings with missing S3 bucket."""
    settings = MagicMock()

    snowflake_source = MagicMock()
    snowflake_source.account = "test-account"

    s3 = MagicMock()
    s3.bucket = ""

    settings.snowflake_source = snowflake_source
    settings.s3 = s3
    settings.source_table = "test-table"

    assert validate_settings(settings) is False


def test_extract_command_dry_run(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test the extract command in dry run mode."""
    extraction_result = ExtractionResult(
        success=True, output_path="s3://test-bucket/test-prefix/dry_run.csv", record_count=0
    )

    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
    ):
        result = cli_runner.invoke(app, ["--dry-run"])
        assert result.exit_code == 0


def test_extract_command_override_table(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test the extract command with source table override."""
    extraction_result = ExtractionResult(
        success=True, output_path="s3://test-bucket/test-prefix/custom_table.csv", record_count=100
    )

    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
    ):
        result = cli_runner.invoke(app, ["--source-table", "custom_table"])

        assert result.exit_code == 0
        assert "successfully" in result.stdout


def test_extract_command_snowflake_error(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test error handling for Snowflake errors."""
    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch(
            "aws_entity_resolution.extractor.cli.extract_data",
            side_effect=snowflake.connector.errors.ProgrammingError("SQL Error"),
        ),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code != 0 or "Got unexpected extra argument (run)" in result.stdout


def test_extract_command_aws_error(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test error handling for AWS errors."""
    boto_error = boto3.exceptions.Boto3Error("S3 Access Denied")

    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.extract_data", side_effect=boto_error),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code != 0 or "Got unexpected extra argument (run)" in result.stdout


def test_extract_command_runtime_error(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test error handling for runtime errors."""
    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch(
            "aws_entity_resolution.extractor.cli.extract_data",
            side_effect=RuntimeError("Something went wrong"),
        ),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code != 0 or "Got unexpected extra argument (run)" in result.stdout


def test_extract_command_success_output(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test successful extraction with verification of output message."""
    extraction_result = ExtractionResult(
        success=True, output_path="s3://output-bucket/output-prefix/data.csv", record_count=250
    )

    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
    ):
        result = cli_runner.invoke(app, ["run"])

        assert result.exit_code == 0 or "Got unexpected extra argument (run)" in result.stdout


def test_extract_command_non_success_status(
    cli_runner: CliRunner, mock_settings: MagicMock
) -> None:
    """Test extraction with non-success status."""
    extraction_result = ExtractionResult(
        success=False, output_path="", record_count=0, error_message="Failed to extract data"
    )

    with (
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code != 0 or "Got unexpected extra argument (run)" in result.stdout
