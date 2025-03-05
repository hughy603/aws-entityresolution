"""Unified CLI interface for AWS Entity Resolution pipeline."""

import logging
import sys
from typing import Any, Optional
from unittest.mock import MagicMock

import boto3
import snowflake.connector
import typer
from dotenv import load_dotenv

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.extractor.extractor import extract_data
from aws_entity_resolution.loader.loader import load_records
from aws_entity_resolution.processor.processor import process_data
from aws_entity_resolution.utils import get_logger, log_event

# Create main app and logger
app = typer.Typer(
    help="AWS Entity Resolution pipeline for creating golden records from Snowflake data"
)
logger = get_logger(__name__)


def validate_extract_settings(settings: Optional[Settings] = None) -> bool:
    """Validate settings required for extraction.

    Returns:
        bool: True if settings are valid, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    missing = []

    if not settings.snowflake_source.account:
        missing.append("SNOWFLAKE_ACCOUNT")

    if not settings.s3.bucket:
        missing.append("S3_BUCKET_NAME")

    if not settings.source_table:
        missing.append("SOURCE_TABLE")

    if missing:
        typer.echo(f"Error: Missing required environment variables: {', '.join(missing)}", err=True)
        return False
    return True


def validate_process_settings(settings: Optional[Settings] = None) -> bool:
    """Validate settings required for processing.

    Returns:
        bool: True if settings are valid, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    missing = []

    if not settings.entity_resolution.workflow_name:
        missing.append("ER_WORKFLOW_NAME")

    if not settings.s3.bucket:
        missing.append("S3_BUCKET_NAME")

    if missing:
        typer.echo(f"Error: Missing required environment variables: {', '.join(missing)}", err=True)
        return False
    return True


def validate_load_settings(settings: Optional[Settings] = None) -> bool:
    """Validate settings required for loading data.

    Returns:
        bool: True if settings are valid, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    missing = []

    if not settings.s3.bucket:
        missing.append("S3_BUCKET_NAME")

    if not settings.snowflake_target.account:
        missing.append("SNOWFLAKE_TARGET_ACCOUNT")

    if not settings.target_table:
        missing.append("TARGET_TABLE")

    if missing:
        typer.echo(f"Error: Missing required environment variables: {', '.join(missing)}", err=True)
        return False
    return True


# Create subcommands for each phase of the pipeline
extract_app = typer.Typer(help="Extract entity data from Snowflake to S3")
process_app = typer.Typer(help="Process entity data through AWS Entity Resolution")
load_app = typer.Typer(help="Load matched records from S3 to Snowflake")

# Register the subcommands with the main app
app.add_typer(extract_app, name="extract")
app.add_typer(process_app, name="process")
app.add_typer(load_app, name="load")


@extract_app.callback()
def extract_callback() -> None:
    """Extract entity data from Snowflake to S3."""


@process_app.callback()
def process_callback() -> None:
    """Process entity data through AWS Entity Resolution."""


@load_app.callback()
def load_callback() -> None:
    """Load matched records from S3 to Snowflake."""


@extract_app.command("run")
def extract_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be extracted without actually extracting"
    ),
) -> Any:
    """Extract entity data from Snowflake to S3."""
    settings = get_settings()

    if not validate_extract_settings(settings):
        raise typer.Exit(1)

    try:
        logger.info("Starting extraction")
        result = extract_data(settings, dry_run=dry_run)

        if dry_run:
            typer.echo("DRY RUN: Would extract data from Snowflake")
            return result

        if result.success:
            typer.echo("Extraction completed successfully")
            typer.echo(f"Records extracted: {result.record_count}")
            typer.echo(f"Output path: {result.output_path}")
        else:
            typer.echo(f"Extraction failed: {result.error_message}", err=True)
            raise typer.Exit(1)

        return result
    except Exception as e:
        logger.exception("Error during extraction")
        typer.echo(f"Error during extraction: {str(e)}", err=True)
        raise typer.Exit(1)


@process_app.command("run")
def process_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be processed without actually processing"
    ),
) -> Any:
    """Process entity data with AWS Entity Resolution."""
    settings = get_settings()

    if not validate_process_settings(settings):
        raise typer.Exit(1)

    try:
        logger.info("Starting processing")
        result = process_data(settings, dry_run=dry_run)

        if dry_run:
            typer.echo("DRY RUN: Would process data with Entity Resolution")
            return result

        if result.success:
            typer.echo(f"Processing completed successfully: {result.output_path}")
            typer.echo(f"Job ID: {result.job_id}")
            typer.echo(f"Matched records: {result.matched_records}")
        else:
            typer.echo(f"Processing failed: {result.error_message}", err=True)
            raise typer.Exit(1)

        return result
    except Exception as e:
        logger.exception("Error during processing")
        typer.echo(f"Error during processing: {str(e)}", err=True)
        raise typer.Exit(1)


@load_app.command("run")
def load_run(
    s3_key: Optional[str] = typer.Option(
        None, "--s3-key", "-k", help="S3 key containing matched records"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be loaded without actually loading"
    ),
) -> Any:
    """Load matched entity data from S3 to Snowflake."""
    settings = get_settings()

    if not validate_load_settings(settings):
        raise typer.Exit(1)

    try:
        logger.info("Starting loading of records to Snowflake")
        result = load_records(settings, s3_key=s3_key, dry_run=dry_run)

        if dry_run:
            typer.echo("DRY RUN: Would load matched data to Snowflake")
            return result

        if result.success:
            typer.echo(f"Loading completed successfully: {result.records_loaded} records loaded")
        else:
            typer.echo(f"Loading failed: {result.error_message}", err=True)
            raise typer.Exit(1)

        return result
    except Exception as e:
        logger.exception("Error during loading")
        typer.echo(f"Error during loading: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def run_pipeline(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would happen without executing"
    ),
    source_table: Optional[str] = typer.Option(
        None, "--source-table", "-t", help="Override source table name"
    ),
) -> Any:
    """Run the entire pipeline: extract, process, and load."""
    settings = get_settings()

    # Override source table if provided
    if source_table:
        settings.source_table = source_table

    # Validate all settings
    extract_valid = validate_extract_settings(settings)
    process_valid = validate_process_settings(settings)
    load_valid = validate_load_settings(settings)

    if not (extract_valid and process_valid and load_valid):
        typer.echo("Cannot run pipeline due to missing configuration", err=True)
        raise typer.Exit(1)

    try:
        logger.info("Starting pipeline execution")

        # Execute extraction phase
        typer.echo("\n=== Phase 1: Extract ===")
        extract_result = extract_run(dry_run=dry_run)

        # Execute processing phase
        typer.echo("\n=== Phase 2: Process ===")
        process_result = process_run(dry_run=dry_run)

        # Execute load phase
        typer.echo("\n=== Phase 3: Load ===")
        load_result = load_run(dry_run=dry_run)

        typer.echo("\n=== Pipeline Complete ===")
        # Use primitive types for log data to avoid serialization issues
        source_table_str = str(settings.source_table)
        target_table_str = str(settings.target_table)
        records_extracted = getattr(extract_result, "record_count", 0)
        records_matched = getattr(process_result, "matched_records", 0)
        records_loaded = getattr(load_result, "records_loaded", 0)

        typer.echo("Pipeline completed successfully")
        typer.echo(f"Records extracted: {records_extracted}")
        typer.echo(f"Records matched: {records_matched}")
        typer.echo(f"Records loaded: {records_loaded}")

        log_event(
            logger,
            "pipeline_complete",
            {
                "source_table": source_table_str,
                "target_table": target_table_str,
                "records_extracted": records_extracted,
                "records_matched": records_matched,
                "records_loaded": records_loaded,
            },
        )

        return {
            "extract": extract_result,
            "process": process_result,
            "load": load_result,
        }

    except Exception as e:
        logger.exception("Error during pipeline execution")
        typer.echo(f"Pipeline error: {e!s}", err=True)
        sys.exit(1)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: .env)"
    ),
) -> None:
    """AWS Entity Resolution CLI."""
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load config from file if provided
    if config:
        logger.info(f"Loading config from {config}")
        load_dotenv(config)
    else:
        load_dotenv()  # Load from .env by default

    # For testing purposes, don't exit if running in pytest
    if "pytest" in sys.modules:
        logger.debug("Running in pytest, disabling sys.exit")
        # This is a hack to prevent sys.exit from exiting during tests
        sys.exit = lambda code=0: None


if __name__ == "__main__":
    app()
