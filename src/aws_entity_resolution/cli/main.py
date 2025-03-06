"""Main CLI entry point for AWS Entity Resolution.

This module provides the main CLI entry point for the AWS Entity Resolution package.
It combines the various sub-commands into a unified CLI interface.
"""

import logging
import os
from typing import Optional

import typer
from dotenv import load_dotenv

from aws_entity_resolution.cli.commands.loader import app as loader_app
from aws_entity_resolution.cli.commands.processor import app as processor_app
from aws_entity_resolution.config.unified import create_settings
from aws_entity_resolution.utils.logging import get_logger

# Create main app and logger
app = typer.Typer(
    help="AWS Entity Resolution pipeline for creating golden records",
    no_args_is_help=True,
)
logger = get_logger(__name__)

# Version information
__version__ = "1.0.0"

# Add sub-apps for each stage
app.add_typer(processor_app, name="process", help="Process data with AWS Entity Resolution")
app.add_typer(loader_app, name="load", help="Load processed data to Snowflake")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (default: .env)",
    ),
    secrets_name: Optional[str] = typer.Option(
        None,
        "--secrets-name",
        "-s",
        help="AWS Secrets Manager secret name",
    ),
) -> None:
    """AWS Entity Resolution CLI for creating golden records.

    This CLI tool provides commands for running the AWS Entity Resolution pipeline,
    which processes data from S3 with AWS Entity Resolution and loads the results
    to Snowflake. Input data is expected to be already available in the S3 bucket.

    Use the --help option with any command to see detailed usage information.
    """
    # Load environment variables from .env file if config not specified
    if not config:
        load_dotenv()

    # Set environment variables for configuration
    if config:
        os.environ["CONFIG_FILE"] = config
    if secrets_name:
        os.environ["AWS_SECRETS_NAME"] = secrets_name

    # Set logging level based on verbose flag
    if verbose:
        logging.getLogger("aws_entity_resolution").setLevel(logging.DEBUG)
    else:
        logging.getLogger("aws_entity_resolution").setLevel(logging.INFO)

    # Log startup information
    settings = create_settings(
        config_file=config,
        aws_secrets_name=secrets_name,
    )

    logger.debug(
        "CLI initialized",
        extra={
            "verbose": verbose,
            "config_file": config,
            "aws_region": settings.aws.region,
            "environment": settings.environment,
            "version": __version__,
        },
    )


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AWS Entity Resolution v{__version__}")


if __name__ == "__main__":
    app()
