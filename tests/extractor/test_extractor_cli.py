"""Tests for the extractor CLI module."""

from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from aws_entity_resolution.extractor.cli import app, extract
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


def test_extract_function_success(mock_settings: MagicMock) -> None:
    """Test the extract function directly."""
    extraction_result = ExtractionResult(
        success=True,
        output_path="s3://test-bucket/test-prefix/extracted_data.csv",
        record_count=100,
    )

    with (
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
        patch("aws_entity_resolution.extractor.cli.typer.echo") as mock_echo,
    ):
        # Call the function directly instead of through the CLI
        extract(source_table=None, query=None, dry_run=False)

        # Check that the success message was echoed
        success_call = any(
            call.args[0].startswith("Successfully extracted 100 records")
            for call in mock_echo.call_args_list
        )
        assert success_call, "Success message not found in output"


def test_extract_function_with_options(mock_settings: MagicMock) -> None:
    """Test the extract function with custom options."""
    extraction_result = ExtractionResult(
        success=True,
        output_path="s3://test-bucket/test-prefix/custom_extract.csv",
        record_count=50,
    )

    with (
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
        patch("aws_entity_resolution.extractor.cli.typer.echo") as mock_echo,
    ):
        # Call the function directly with options
        extract(source_table="custom_table", query=None, dry_run=False)

        # Check that the success message was echoed
        success_call = any(
            call.args[0].startswith("Successfully extracted 50 records")
            for call in mock_echo.call_args_list
        )
        assert success_call, "Success message not found in output"


def test_extract_function_error(mock_settings: MagicMock) -> None:
    """Test the extract function with an error."""
    extraction_result = ExtractionResult(
        success=False,
        error_message="Failed to connect to Snowflake",
    )

    with (
        patch("aws_entity_resolution.extractor.cli.extract_data", return_value=extraction_result),
        patch("aws_entity_resolution.extractor.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.extractor.cli.validate_settings", return_value=True),
        patch("aws_entity_resolution.extractor.cli.typer.echo") as mock_echo,
        pytest.raises(typer.Exit),  # Expect typer.Exit to be raised
    ):
        # Call the function directly
        extract(source_table=None, query=None, dry_run=False)

        # Check that the error message was echoed
        error_call = any(
            call.args[0].startswith("Error extracting data: Failed to connect to Snowflake")
            for call in mock_echo.call_args_list
        )
        assert error_call, "Error message not found in output"


@pytest.mark.skip("Version command not implemented yet")
def test_version_command(cli_runner: CliRunner) -> None:
    """Test the version command."""
    result = cli_runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AWS Entity Resolution Extractor" in result.stdout
