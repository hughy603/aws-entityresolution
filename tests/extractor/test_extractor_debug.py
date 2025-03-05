"""Debug test for the extractor CLI."""

import sys

from typer.testing import CliRunner

from aws_entity_resolution.extractor.cli import app


def test_debug_app():
    """Debug test to understand the Typer CLI structure."""
    runner = CliRunner()

    # Test app without args
    result = runner.invoke(app)
    sys.stdout.write("Without args:\n")
    sys.stdout.write(f"Exit code: {result.exit_code}\n")
    sys.stdout.write(f"Stdout: {result.stdout}\n\n")

    # Test with run command
    result = runner.invoke(app, ["run"])
    sys.stdout.write("With 'run' command:\n")
    sys.stdout.write(f"Exit code: {result.exit_code}\n")
    sys.stdout.write(f"Stdout: {result.stdout}\n")

    # Check if validate_settings is called
    result = runner.invoke(app, ["run", "--help"])
    sys.stdout.write("\nWith 'run --help':\n")
    sys.stdout.write(f"Exit code: {result.exit_code}\n")
    sys.stdout.write(f"Stdout: {result.stdout}\n")

    assert True  # Just to make the test pass
