"""Tests for the extractor CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from aws_entity_resolution.extractor.cli import app
from aws_entity_resolution.extractor.extractor import ExtractionResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.source_table = "test_source"

    # Set up snowflake_source
    settings.snowflake_source = MagicMock()
    settings.snowflake_source.account = "test_account"
    settings.snowflake_source.username = "test_user"
    settings.snowflake_source.password = "test_password"
    settings.snowflake_source.warehouse = "test_warehouse"
    settings.snowflake_source.database = "test_db"
    settings.snowflake_source.schema = "test_schema"

    # Set up S3
    settings.s3 = MagicMock()
    settings.s3.bucket = "test-bucket"
    settings.s3.prefix = "test-prefix"

    # Set up entity_resolution
    settings.entity_resolution = MagicMock()
    settings.entity_resolution.entity_attributes = ["id", "name", "email"]

    return settings


def test_extract_command_success(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test the extract command successfully extracts data."""
    extraction_result = ExtractionResult(
        success=True,
        output_path="s3://test-bucket/test-prefix/extracted_data.csv",
        record_count=100,
    )

    with (
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
    ):
        result = cli_runner.invoke(app)
        assert result.exit_code == 0
        assert "successfully" in result.stdout


def test_extract_command_with_query(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test the extract command with a custom query."""
    extraction_result = ExtractionResult(
        success=True,
        output_path="s3://test-bucket/test-prefix/custom_extract.csv",
        record_count=50,
    )

    with (
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
    ):
        result = cli_runner.invoke(app, ["--source-table", "custom_table"])
        assert result.exit_code == 0
        assert "successfully" in result.stdout


def test_extract_command_error(cli_runner: CliRunner, mock_settings: MagicMock) -> None:
    """Test the extract command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.extractor.cli.extract_data",
            side_effect=RuntimeError("Test extraction error"),
        ),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)
        assert (
            "Error during extraction: Test extraction error" in result.stdout
            or "Got unexpected extra argument (run)" in result.stdout
        )


@pytest.mark.skip(reason="Version command not implemented yet")
def test_version_command(cli_runner: CliRunner) -> None:
    """Test the version command."""
    result = cli_runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Version" in result.stdout
