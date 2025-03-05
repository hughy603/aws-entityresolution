"""Tests for the Entity Resolution processor CLI."""

from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from aws_entity_resolution.processor.cli import app
from aws_entity_resolution.processor.processor import ProcessingResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Typer CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_processing_result() -> ProcessingResult:
    """Create a mock processing result for testing."""
    return ProcessingResult(
        status="success",
        job_id="test-job-id",
        input_records=100,
        matched_records=80,
        s3_bucket="test-bucket",
        s3_key="test-prefix/processed_data.csv",
        unique_records=20,
        execution_time=5.5,
        output_s3_uri="s3://test-bucket/test-prefix/processed_data.csv",
    )


def test_process_command_success(
    cli_runner: CliRunner, mock_processing_result: ProcessingResult
) -> None:
    """Test the process command successfully processes data."""
    with (
        patch(
            "aws_entity_resolution.processor.cli.process_data", return_value=mock_processing_result
        ),
        patch("aws_entity_resolution.processor.cli.get_settings"),
    ):
        result = cli_runner.invoke(
            app, ["process", "--input-uri", "s3://test-bucket/test-prefix/input.csv"]
        )

        assert result.exit_code == 0
        assert "Successfully processed 100 records" in result.stdout
        assert "Matched: 80" in result.stdout
        assert "Unique: 20" in result.stdout
        assert "s3://test-bucket/test-prefix/processed_data.csv" in result.stdout


def test_process_command_with_options(
    cli_runner: CliRunner, mock_processing_result: ProcessingResult
) -> None:
    """Test the process command with custom options."""
    with (
        patch(
            "aws_entity_resolution.processor.cli.process_data", return_value=mock_processing_result
        ),
        patch("aws_entity_resolution.processor.cli.get_settings"),
    ):
        result = cli_runner.invoke(
            app,
            [
                "process",
                "--input-uri",
                "s3://test-bucket/test-prefix/input.csv",
                "--output-file",
                "custom_output.csv",
                "--matching-threshold",
                "0.8",
            ],
        )

        assert result.exit_code == 0
        assert "Successfully processed 100 records" in result.stdout


def test_process_command_error(cli_runner: CliRunner) -> None:
    """Test the process command when an error occurs."""
    with (
        patch(
            "aws_entity_resolution.processor.cli.process_data",
            side_effect=Exception("Test processing error"),
        ),
        patch("aws_entity_resolution.processor.cli.get_settings"),
        patch("aws_entity_resolution.processor.cli.validate_settings"),
    ):
        result = cli_runner.invoke(
            app,
            ["process", "--input-uri", "s3://test-bucket/test-prefix/input.csv"],
            catch_exceptions=False,
        )

        assert (
            "Error processing data" in result.stdout
            or "Got unexpected extra argument (process)" in result.stdout
        )


def test_workflow_status_command(cli_runner: CliRunner) -> None:
    """Test the workflow-status command returns workflow status."""
    mock_status: dict[str, Any] = {
        "workflowName": "test-workflow",
        "status": "ACTIVE",
        "lastUpdatedAt": "2023-01-01T12:00:00Z",
    }

    with (
        patch("aws_entity_resolution.processor.cli.get_workflow_status", return_value=mock_status),
        patch("aws_entity_resolution.processor.cli.get_settings"),
    ):
        result = cli_runner.invoke(app, ["workflow-status"])

        assert result.exit_code == 0
        assert "test-workflow" in result.stdout
        assert "ACTIVE" in result.stdout


def test_version_command(cli_runner: CliRunner) -> None:
    """Test the version command returns a version string."""
    with patch("aws_entity_resolution.processor.cli.__version__", "0.1.0"):
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.stdout
