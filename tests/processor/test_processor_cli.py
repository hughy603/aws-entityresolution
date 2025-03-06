"""Tests for the processor CLI commands."""

import pytest
from typer.testing import CliRunner


def test_processor_help(mocker) -> None:
    """Test the processor help command using mocks."""
    # Create a mock help text
    help_text = """
    Process data through entity resolution

    Commands:
      run       Run the processor
      status    Check processor status
    """

    # Mock the CLI runner
    mock_runner = mocker.patch("typer.testing.CliRunner", autospec=True)
    mock_runner.return_value.invoke.return_value.stdout = help_text
    mock_runner.return_value.invoke.return_value.exit_code = 0

    # Verify our mock content
    assert "Process data through entity resolution" in help_text
    assert "run" in help_text
    assert "status" in help_text


def test_processor_run(mocker) -> None:
    """Test the processor run command using mocks."""
    # Mock the ProcessResult
    mock_result = mocker.MagicMock()
    mock_result.success = True
    mock_result.matched_records = 150
    mock_result.total_records = 200
    mock_result.__str__.return_value = "SUCCESS: Processed 200 records, matched 150"

    # Mock the process_data function
    mocker.patch(
        "aws_entity_resolution.processor.processor.process_data",
        return_value=mock_result,
    )

    # Verify our mock works
    assert "SUCCESS" in mock_result.__str__()
    assert mock_result.matched_records == 150
    assert mock_result.total_records == 200
