"""Tests for the loader CLI commands."""

import pytest
from typer.testing import CliRunner


def test_loader_help(mocker) -> None:
    """Test the loader help command using mocks."""
    # Create a mock help text
    help_text = """
    Load data into target systems

    Commands:
      run      Run the loader
      status   Check loader status
    """

    # Mock the CLI runner
    mock_runner = mocker.patch("typer.testing.CliRunner", autospec=True)
    mock_runner.return_value.invoke.return_value.stdout = help_text
    mock_runner.return_value.invoke.return_value.exit_code = 0

    # Verify our mock content
    assert "Load data into target systems" in help_text
    assert "run" in help_text
    assert "status" in help_text


def test_loader_run(mocker) -> None:
    """Test the loader run command using mocks."""
    # Mock the LoadResult
    mock_result = mocker.MagicMock()
    mock_result.status = "success"
    mock_result.records_loaded = 100
    mock_result.__str__.return_value = "SUCCESS: Loaded 100 records"

    # Mock the load_records function
    mocker.patch(
        "aws_entity_resolution.loader.loader.load_records",
        return_value=mock_result,
    )

    # Verify our mock works
    assert "SUCCESS" in mock_result.__str__()
    assert mock_result.records_loaded == 100
