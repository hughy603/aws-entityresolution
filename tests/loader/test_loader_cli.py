"""Tests for the Entity Resolution loader CLI."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from aws_entity_resolution.loader.cli import app
from aws_entity_resolution.loader.loader import LoadingResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Typer CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_loading_result() -> LoadingResult:
    """Create a mock loading result for testing."""
    return LoadingResult(
        status="success",
        records_loaded=150,
        target_table="GOLDEN_ENTITY_RECORDS",
        error_message=None,
        execution_time=3.2,
    )


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.target_table = "GOLDEN_ENTITY_RECORDS"
    settings.s3.bucket = "test-bucket"
    return settings


def test_load_command_success(
    cli_runner: CliRunner, mock_loading_result: LoadingResult, mock_settings
) -> None:
    """Test the load command successfully loads data."""
    with (
        patch("aws_entity_resolution.loader.cli.load_records", return_value=mock_loading_result),
        patch("aws_entity_resolution.loader.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.loader.cli.validate_settings", return_value=True),
    ):
        # Set success property on the mock result
        mock_loading_result.success = True
        mock_loading_result.record_count = 150

        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Successfully loaded" in result.stdout
        assert "GOLDEN_ENTITY_RECORDS" in result.stdout


def test_load_command_with_options(
    cli_runner: CliRunner, mock_loading_result: LoadingResult, mock_settings
) -> None:
    """Test the load command with custom options."""
    with (
        patch("aws_entity_resolution.loader.cli.load_records", return_value=mock_loading_result),
        patch("aws_entity_resolution.loader.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.loader.cli.validate_settings", return_value=True),
    ):
        # Set success property on the mock result
        mock_loading_result.success = True
        mock_loading_result.record_count = 150

        result = cli_runner.invoke(
            app,
            [
                "run",
                "--s3-key",
                "test-prefix/matched_records.csv",
                "--target-table",
                "CUSTOM_TARGET",
                "--truncate",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Successfully loaded" in result.stdout


def test_load_command_error(cli_runner: CliRunner, mock_settings) -> None:
    """Test the load command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.loader.cli.load_records",
            side_effect=Exception("Test loading error"),
        ),
        patch("aws_entity_resolution.loader.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.loader.cli.validate_settings", return_value=True),
    ):
        result = cli_runner.invoke(app, ["run"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "Error: Test loading error" in result.stdout


def test_create_table_command(cli_runner: CliRunner, mock_settings) -> None:
    """Test the create-table command successfully creates a table."""
    mock_result = LoadingResult(
        status="success",
        records_loaded=0,
        target_table="GOLDEN_ENTITY_RECORDS",
        error_message=None,
        execution_time=1.0,
    )
    mock_result.success = True
    mock_result.sql = "CREATE TABLE IF NOT EXISTS GOLDEN_ENTITY_RECORDS..."

    with (
        patch("aws_entity_resolution.loader.cli.create_target_table", return_value=mock_result),
        patch("aws_entity_resolution.loader.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.loader.cli.validate_settings", return_value=True),
        # Patch typer.Exit to prevent actual exit
        patch("typer.Exit", side_effect=lambda code=0: None),
    ):
        result = cli_runner.invoke(app, ["create-table"], catch_exceptions=False)

        assert "Successfully created table" in result.stdout


def test_create_table_command_error(cli_runner: CliRunner, mock_settings) -> None:
    """Test the create-table command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.loader.cli.create_target_table",
            side_effect=Exception("Test table creation error"),
        ),
        patch("aws_entity_resolution.loader.cli.get_settings", return_value=mock_settings),
        patch("aws_entity_resolution.loader.cli.validate_settings", return_value=True),
    ):
        result = cli_runner.invoke(app, ["create-table"], catch_exceptions=True)

        assert result.exit_code == 1
        assert "Error: Test table creation error" in result.stdout


def test_version_command(cli_runner: CliRunner) -> None:
    """Test the version command returns a version string."""
    with patch("aws_entity_resolution.loader.cli.__version__", "0.1.0"):
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.stdout
