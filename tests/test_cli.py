"""Tests for the CLI module."""

import json
from unittest.mock import MagicMock, patch

import pytest
import typer
from src.aws_entity_resolution.cli import (
    app,
    extract_run,
    load_run,
    process_run,
    run_pipeline,
    validate_extract_settings,
    validate_load_settings,
    validate_process_settings,
)
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.source_table = "test_source"
    settings.target_table = "test_target"
    settings.aws_region = "us-east-1"

    # Set up snowflake_source
    settings.snowflake_source = MagicMock()
    settings.snowflake_source.account = "test_account"
    settings.snowflake_source.username = "test_user"
    settings.snowflake_source.password = "test_password"
    settings.snowflake_source.warehouse = "test_warehouse"
    settings.snowflake_source.database = "test_db"
    settings.snowflake_source.schema = "test_schema"

    # Set up snowflake_target
    settings.snowflake_target = MagicMock()
    settings.snowflake_target.account = "test_account"
    settings.snowflake_target.username = "test_user"
    settings.snowflake_target.password = "test_password"
    settings.snowflake_target.warehouse = "test_warehouse"
    settings.snowflake_target.database = "test_db"
    settings.snowflake_target.schema = "test_schema"

    # Set up S3
    settings.s3 = MagicMock()
    settings.s3.bucket = "test-bucket"
    settings.s3.prefix = "test-prefix"

    # Set up AWS
    settings.aws = MagicMock()
    settings.aws.entity_resolution_workflow = "test-workflow"

    # Set up entity_resolution
    settings.entity_resolution = MagicMock()
    settings.entity_resolution.workflow_name = "test-workflow"
    settings.entity_resolution.entity_attributes = ["id", "name", "email"]

    return settings


@pytest.fixture
def mock_extract_result():
    """Create a mock extraction result."""
    return MagicMock()


@pytest.fixture
def mock_process_result():
    """Create a mock process result."""
    result = MagicMock()
    result.status = "success"
    result.job_id = "test-job-id"
    result.input_records = 100
    result.matched_records = 50
    result.s3_bucket = "test-bucket"
    result.s3_key = "test-prefix/output/matches.csv"
    return result


@pytest.fixture
def mock_load_result():
    """Create a mock load result."""
    result = MagicMock()
    result.status = "success"
    result.records_loaded = 50
    result.target_table = "test-target-table"
    return result


def test_validate_extract_settings(mock_settings):
    """Test validation of extract settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        # Valid settings
        assert validate_extract_settings() is True

        # Invalid settings
        mock_settings.source_table = ""
        assert validate_extract_settings() is False

        mock_settings.source_table = "test_source"
        mock_settings.snowflake_source.account = ""
        assert validate_extract_settings() is False


def test_validate_process_settings(mock_settings):
    """Test validation of process settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        # Valid settings
        assert validate_process_settings() is True

        # Invalid settings
        mock_settings.s3.bucket = ""
        assert validate_process_settings() is False


def test_validate_load_settings(mock_settings):
    """Test validation of load settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        # Valid settings
        assert validate_load_settings() is True

        # Invalid settings
        mock_settings.target_table = ""
        assert validate_load_settings() is False

        mock_settings.target_table = "test_target"
        mock_settings.snowflake_target.account = ""
        assert validate_load_settings() is False


def test_extract_run_success(mock_settings, mock_extract_result):
    """Test successful extract run."""
    # Configure the mock result
    mock_extract_result.success = True
    mock_extract_result.output_path = "s3://test-bucket/test-prefix/data.json"
    mock_extract_result.record_count = 100

    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.extract_data", return_value=mock_extract_result),
    ):
        # Call the function
        extract_run(dry_run=False)
        # No assertion needed as we're just checking it doesn't raise an exception


def test_extract_run_dry_run(mock_settings, mock_extract_result):
    """Test extract dry run."""
    # Configure the mock result
    mock_extract_result.success = True
    mock_extract_result.output_path = "s3://test-bucket/test-prefix"

    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.extract_data", return_value=mock_extract_result),
    ):
        # Call the function
        extract_run(dry_run=True)
        # No assertion needed as we're just checking it doesn't raise an exception


def test_extract_run_invalid_settings(mock_settings):
    """Test extract run with invalid settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        mock_settings.source_table = ""
        with pytest.raises(typer.Exit):
            extract_run(dry_run=False)


def test_process_run_success(mock_settings, mock_process_result):
    """Test successful process run."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.process_data", return_value=mock_process_result),
    ):
        result = process_run(dry_run=False)
        assert result.status == "success"
        assert result.job_id == "test-job-id"


def test_process_run_dry_run(mock_settings):
    """Test process dry run."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        result = process_run(dry_run=True)
        assert result.status == "dry_run"


def test_process_run_invalid_settings(mock_settings):
    """Test process run with invalid settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        mock_settings.s3.bucket = ""
        with pytest.raises(typer.Exit):
            process_run(dry_run=False)


def test_load_run_success(mock_settings, mock_load_result):
    """Test successful load run."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.load_records", return_value=mock_load_result),
    ):
        result = load_run(dry_run=False)
        assert result.status == "success"
        assert result.records_loaded == 50


def test_load_run_dry_run(mock_settings):
    """Test load dry run."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        result = load_run(dry_run=True)
        assert result.status == "dry_run"


def test_load_run_invalid_settings(mock_settings):
    """Test load run with invalid settings."""
    with patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings):
        mock_settings.target_table = ""
        with pytest.raises(typer.Exit):
            load_run(dry_run=False)


def test_run_pipeline_success(
    mock_settings, mock_extract_result, mock_process_result, mock_load_result
):
    """Test successful pipeline run."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.extract_run", return_value=mock_extract_result),
        patch("src.aws_entity_resolution.cli.process_run", return_value=mock_process_result),
        patch("src.aws_entity_resolution.cli.load_run", return_value=mock_load_result),
    ):
        # Configure the mock returns
        mock_extract_result.status = "success"
        mock_process_result.status = "success"
        mock_load_result.status = "success"

        result = run_pipeline(dry_run=False)

        # Verify the result contains the mocks
        assert result["extract"] is mock_extract_result
        assert result["process"] is mock_process_result
        assert result["load"] is mock_load_result


def test_run_pipeline_dry_run(mock_settings):
    """Test pipeline dry run."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.extract_run") as mock_extract,
        patch("src.aws_entity_resolution.cli.process_run") as mock_process,
        patch("src.aws_entity_resolution.cli.load_run") as mock_load,
    ):
        # Configure the mock returns
        extract_mock = MagicMock()
        extract_mock.status = "dry_run"
        process_mock = MagicMock()
        process_mock.status = "dry_run"
        load_mock = MagicMock()
        load_mock.status = "dry_run"

        mock_extract.return_value = extract_mock
        mock_process.return_value = process_mock
        mock_load.return_value = load_mock

        result = run_pipeline(dry_run=True)

        # Verify the mocks were called with dry_run=True
        mock_extract.assert_called_once_with(dry_run=True)
        mock_process.assert_called_once_with(dry_run=True)
        mock_load.assert_called_once_with(dry_run=True)

        # Verify the result contains the mocks
        assert result["extract"] is extract_mock
        assert result["process"] is process_mock
        assert result["load"] is load_mock


def test_cli_extract_command(runner, mock_settings, mock_extract_result):
    """Test CLI extract command."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch(
            "src.aws_entity_resolution.cli.extract_data",
            return_value=MagicMock(
                success=True, record_count=100, output_path="s3://test-bucket/test-path"
            ),
        ),
        patch("src.aws_entity_resolution.cli.extract_run", return_value=mock_extract_result),
    ):
        result = runner.invoke(app, ["extract", "run"])
        assert result.exit_code == 0
        assert "Records extracted: 100" in result.stdout


def test_cli_extract_command_dry_run(runner, mock_settings):
    """Test CLI extract command with dry run."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch(
            "src.aws_entity_resolution.cli.extract_data", return_value=MagicMock(status="dry_run")
        ),
        patch("src.aws_entity_resolution.cli.extract_run") as mock_extract,
    ):
        mock_extract.return_value = MagicMock(status="dry_run")

        # Update to use the correct command structure
        result = runner.invoke(app, ["extract", "run", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.stdout


def test_cli_process_command(runner, mock_settings, mock_process_result):
    """Test CLI process command."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch(
            "src.aws_entity_resolution.cli.process_data",
            return_value=MagicMock(success=True, job_id="test-job-id", matched_records=75),
        ),
        patch("src.aws_entity_resolution.cli.process_run", return_value=mock_process_result),
    ):
        # Update to use the correct command structure
        result = runner.invoke(app, ["process", "run"])
        assert result.exit_code == 0
        assert "Job ID: test-job-id" in result.stdout


def test_cli_load_command(runner, mock_settings, mock_load_result):
    """Test CLI load command."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch(
            "src.aws_entity_resolution.cli.load_records",
            return_value=MagicMock(success=True, records_loaded=50),
        ),
        patch("src.aws_entity_resolution.cli.load_run", return_value=mock_load_result),
    ):
        # Update to use the correct command structure
        result = runner.invoke(app, ["load", "run"])
        assert result.exit_code == 0
        assert "Loading completed successfully: 50 records loaded" in result.stdout


def test_cli_run_command(
    runner, mock_settings, mock_extract_result, mock_process_result, mock_load_result
):
    """Test CLI run command."""
    with (
        patch("src.aws_entity_resolution.cli.get_settings", return_value=mock_settings),
        patch("src.aws_entity_resolution.cli.extract_run", return_value=mock_extract_result),
        patch("src.aws_entity_resolution.cli.process_run", return_value=mock_process_result),
        patch("src.aws_entity_resolution.cli.load_run", return_value=mock_load_result),
        patch(
            "src.aws_entity_resolution.cli.extract_data",
            return_value=MagicMock(
                success=True, record_count=100, output_path="s3://test-bucket/test-path"
            ),
        ),
        patch(
            "src.aws_entity_resolution.cli.process_data",
            return_value=MagicMock(success=True, job_id="test-job-id", matched_records=75),
        ),
        patch(
            "src.aws_entity_resolution.cli.load_records",
            return_value=MagicMock(success=True, records_loaded=50),
        ),
    ):
        # Update to use the correct command name
        result = runner.invoke(app, ["run-pipeline"])
        assert result.exit_code == 0
        assert "Pipeline completed successfully" in result.stdout
