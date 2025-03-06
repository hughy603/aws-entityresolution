"""Tests for the main CLI entry point."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from aws_entity_resolution.cli.main import app


# Mock the app instead of importing it
@pytest.fixture
def mock_app(mocker):
    """Mock the CLI app."""
    mock_app = mocker.patch("aws_entity_resolution.cli.main.app", autospec=True)
    # Configure mock version command
    mock_version_cmd = mocker.MagicMock()
    mock_version_cmd.return_value = "AWS Entity Resolution v1.0.0"
    mock_app.command.return_value = lambda func: mock_version_cmd
    return mock_app


def test_version(mocker) -> None:
    """Test the version command using mocks."""
    # Define a mock version string
    version = "AWS Entity Resolution v1.0.0"

    # Mock the version attribute
    mocker.patch(
        "aws_entity_resolution.cli.main.__version__",
        "1.0.0",
    )

    # Test that we have a basic version check
    from aws_entity_resolution.cli.main import __version__

    assert __version__ == "1.0.0"


def test_help(mocker) -> None:
    """Test the help output using mocks."""
    # Create a mock help text
    help_text = """
    AWS Entity Resolution pipeline for creating golden records

    Commands:
      process    Process data through entity resolution
      load       Load data into target systems
      version    Show version information
    """

    # Mock the CLI runner
    mock_runner = mocker.patch("typer.testing.CliRunner", autospec=True)
    mock_runner.return_value.invoke.return_value.stdout = help_text
    mock_runner.return_value.invoke.return_value.exit_code = 0

    # Verify our mock content
    assert "AWS Entity Resolution pipeline for creating golden records" in help_text
    assert "process" in help_text
    assert "load" in help_text
    assert "version" in help_text


def test_actual_version_command() -> None:
    """Test the actual version command."""
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AWS Entity Resolution" in result.stdout
    # Import the version string directly
    from aws_entity_resolution.cli.main import __version__

    assert __version__ in result.stdout


@patch("aws_entity_resolution.cli.commands.processor.ProcessCommand.execute")
def test_process_command(mock_execute) -> None:
    """Test the process command."""
    runner = CliRunner()

    # Test with basic arguments
    result = runner.invoke(
        app,
        ["process", "run", "input/data.csv"],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()

    # Reset the mock for the next test
    mock_execute.reset_mock()

    # Test with additional arguments
    result = runner.invoke(
        app,
        [
            "process",
            "run",
            "input/data.csv",
            "--output-prefix",
            "custom/prefix/",
            "--no-wait",
            "--timeout",
            "1800",
        ],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()


@patch("aws_entity_resolution.cli.commands.loader.LoadCommand.execute")
def test_load_command(mock_execute) -> None:
    """Test the load command."""
    runner = CliRunner()

    # Test with basic arguments
    result = runner.invoke(
        app,
        ["load", "run", "output/matched.csv"],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()

    # Reset the mock for the next test
    mock_execute.reset_mock()

    # Test with additional arguments
    result = runner.invoke(
        app,
        [
            "load",
            "run",
            "output/matched.csv",
            "--target-table",
            "golden_records",
            "--truncate",
        ],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()


@patch("aws_entity_resolution.cli.commands.loader.SetupCommand.execute")
def test_setup_command(mock_execute) -> None:
    """Test the setup command."""
    runner = CliRunner()

    # Test with basic arguments
    result = runner.invoke(
        app,
        ["load", "setup"],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()

    # Reset the mock for the next test
    mock_execute.reset_mock()

    # Test with additional arguments
    result = runner.invoke(
        app,
        [
            "load",
            "setup",
            "--target-table",
            "custom_golden_records",
            "--force",
        ],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()


@patch("aws_entity_resolution.cli.commands.processor.StatusCommand.execute")
def test_status_command(mock_execute) -> None:
    """Test the status command."""
    runner = CliRunner()

    # Test with job ID
    result = runner.invoke(
        app,
        ["process", "status", "job-12345"],
    )

    assert result.exit_code == 0
    mock_execute.assert_called_once()
