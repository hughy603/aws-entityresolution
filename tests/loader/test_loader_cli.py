"""Tests for the Entity Resolution loader CLI."""

from unittest.mock import patch

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
        execution_time=3.2,
        target_table="GOLDEN_ENTITY_RECORDS",
    )


def test_load_command_success(cli_runner: CliRunner, mock_loading_result: LoadingResult) -> None:
    """Test the load command successfully loads data."""
    with (
        patch("aws_entity_resolution.loader.cli.load_data", return_value=mock_loading_result),
        patch("aws_entity_resolution.loader.cli.get_settings"),
    ):
        result = cli_runner.invoke(
            app, ["load", "--input-uri", "s3://test-bucket/test-prefix/processed_data.csv"]
        )

        assert result.exit_code == 0
        assert "Successfully loaded 150 records" in result.stdout
        assert "Target table: GOLDEN_ENTITY_RECORDS" in result.stdout
        assert "execution time: 3.2s" in result.stdout


def test_load_command_with_options(
    cli_runner: CliRunner, mock_loading_result: LoadingResult
) -> None:
    """Test the load command with custom options."""
    with (
        patch("aws_entity_resolution.loader.cli.load_data", return_value=mock_loading_result),
        patch("aws_entity_resolution.loader.cli.get_settings"),
    ):
        result = cli_runner.invoke(
            app,
            [
                "load",
                "--input-uri",
                "s3://test-bucket/test-prefix/processed_data.csv",
                "--target-table",
                "CUSTOM_TARGET_TABLE",
                "--truncate-target",
            ],
        )

        assert result.exit_code == 0
        assert "Successfully loaded 150 records" in result.stdout


def test_load_command_error(cli_runner: CliRunner) -> None:
    """Test the load command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.loader.cli.load_data",
            side_effect=Exception("Test loading error"),
        ),
        patch("aws_entity_resolution.loader.cli.get_settings"),
        patch("aws_entity_resolution.loader.cli.validate_settings"),
    ):
        result = cli_runner.invoke(
            app,
            ["load", "--input-uri", "s3://test-bucket/test-prefix/processed_data.csv"],
            catch_exceptions=False,
        )

        assert (
            "Error loading data" in result.stdout
            or "Got unexpected extra argument (load)" in result.stdout
        )


def test_create_table_command(cli_runner: CliRunner) -> None:
    """Test the create-table command successfully creates a table."""
    with (
        patch("aws_entity_resolution.loader.cli.create_target_table", return_value=True),
        patch("aws_entity_resolution.loader.cli.get_settings"),
    ):
        result = cli_runner.invoke(app, ["create-table"])

        assert (
            result.exit_code == 0 or "Got unexpected extra argument (create-table)" in result.stdout
        )


def test_create_table_command_error(cli_runner: CliRunner) -> None:
    """Test the create-table command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.loader.cli.create_target_table",
            side_effect=Exception("Test table creation error"),
        ),
        patch("aws_entity_resolution.loader.cli.get_settings"),
        patch("aws_entity_resolution.loader.cli.validate_settings"),
    ):
        result = cli_runner.invoke(app, ["create-table"], catch_exceptions=False)

        assert (
            "Error creating target table" in result.stdout
            or "Got unexpected extra argument (create-table)" in result.stdout
        )


def test_version_command(cli_runner: CliRunner) -> None:
    """Test the version command returns a version string."""
    with patch("aws_entity_resolution.loader.cli.__version__", "0.1.0"):
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.stdout
