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

# Create sub-apps for each stage
extract_app = typer.Typer(help="Extract entity data from Snowflake to S3")
process_app = typer.Typer(help="Process entity data through AWS Entity Resolution")
load_app = typer.Typer(help="Load matched records from S3 to Snowflake")

# Add sub-apps to main app
app.add_typer(extract_app, name="extract")
app.add_typer(process_app, name="process")
app.add_typer(load_app, name="load")


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


@extract_app.callback()
def extract_callback() -> None:
    """Extract entity data from Snowflake to S3."""
    pass


@process_app.callback()
def process_callback() -> None:
    """Process entity data through AWS Entity Resolution."""
    pass


@load_app.callback()
def load_callback() -> None:
    """Load matched records from S3 to Snowflake."""
    pass


@extract_app.command("run")
def extract_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be extracted without actually extracting"
    ),
    source_table: Optional[str] = typer.Option(
        None, "--source-table", "-t", help="Override source table name"
    ),
    query: Optional[str] = typer.Option(
        None, "--query", "-q", help="Custom SQL query to extract data (overrides source table)"
    ),
) -> Any:
    """Extract entity data from Snowflake to S3."""
    try:
        settings = get_settings()

        if not validate_extract_settings(settings):
            raise typer.Exit(1)

        # Override source table if provided
        if source_table:
            settings.source_table = source_table

        # Log the extraction parameters
        log_event(
            logger,
            "Starting data extraction",
            {
                "source_table": settings.source_table,
                "s3_bucket": settings.s3.bucket,
                "dry_run": dry_run,
            },
        )

        # Extract the data
        result = extract_data(settings, query=query, dry_run=dry_run)

        if result.success:
            typer.echo(
                f"Successfully extracted {result.record_count} records to {result.output_path}"
            )
            if dry_run:
                typer.echo("This was a dry run. No data was actually extracted.")
        else:
            typer.echo(f"Error extracting data: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@process_app.command("run")
def process_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be processed without actually processing"
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for processing to complete"),
    input_uri: Optional[str] = typer.Option(
        None, "--input-uri", "-i", help="URI of input data (s3://bucket/key)"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output-file", "-o", help="Custom output filename"
    ),
    matching_threshold: Optional[float] = typer.Option(
        None, "--threshold", "-t", help="Matching confidence threshold"
    ),
) -> Any:
    """Process entity data through AWS Entity Resolution."""
    try:
        settings = get_settings()

        if not validate_process_settings(settings):
            raise typer.Exit(1)

        # Log the processing parameters
        log_event(
            logger,
            "Starting data processing",
            {
                "workflow_name": settings.entity_resolution.workflow_name,
                "s3_bucket": settings.s3.bucket,
                "dry_run": dry_run,
                "wait": wait,
            },
        )

        # Process the data
        result = process_data(
            settings,
            dry_run=dry_run,
            wait=wait,
            input_uri=input_uri,
            output_file=output_file,
            matching_threshold=matching_threshold,
        )

        if result.success:
            typer.echo(f"Successfully processed data: {result.output_path}")
            if result.job_id:
                typer.echo(f"Job ID: {result.job_id}")
            if dry_run:
                typer.echo("This was a dry run. No data was actually processed.")
            return result
        else:
            typer.echo(f"Error processing data: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@load_app.command("run")
def load_run(
    s3_key: Optional[str] = typer.Option(
        None, "--s3-key", "-k", help="S3 key containing matched records"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be loaded without actually loading"
    ),
    target_table: Optional[str] = typer.Option(
        None, "--target-table", "-t", help="Override target table name"
    ),
    truncate_target: bool = typer.Option(
        False, "--truncate", help="Truncate target table before loading"
    ),
) -> Any:
    """Load matched records from S3 to Snowflake."""
    try:
        settings = get_settings()

        if not validate_load_settings(settings):
            raise typer.Exit(1)

        # Override target table if provided
        if target_table:
            settings.target_table = target_table

        # Log the loading parameters
        log_event(
            logger,
            "Starting data loading",
            {
                "s3_bucket": settings.s3.bucket,
                "s3_key": s3_key,
                "target_table": settings.target_table,
                "dry_run": dry_run,
                "truncate": truncate_target,
            },
        )

        # Load the data
        result = load_records(
            settings,
            s3_key=s3_key,
            dry_run=dry_run,
        )

        if result.success:
            typer.echo(
                f"Successfully loaded {result.record_count} records to {settings.target_table}"
            )
            if dry_run:
                typer.echo("This was a dry run. No data was actually loaded.")
            return result
        else:
            typer.echo(f"Error loading data: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def run_pipeline(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would happen without executing"
    ),
    source_table: Optional[str] = typer.Option(
        None, "--source-table", "-t", help="Override source table name"
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for processing to complete"),
) -> Any:
    """Run the complete entity resolution pipeline."""
    try:
        settings = get_settings()

        # Validate all settings
        extract_valid = validate_extract_settings(settings)
        process_valid = validate_process_settings(settings)
        load_valid = validate_load_settings(settings)

        if not (extract_valid and process_valid and load_valid):
            raise typer.Exit(1)

        # Override source table if provided
        if source_table:
            settings.source_table = source_table

        # Log the pipeline parameters
        log_event(
            logger,
            "Starting pipeline execution",
            {
                "source_table": settings.source_table,
                "s3_bucket": settings.s3.bucket,
                "target_table": settings.target_table,
                "dry_run": dry_run,
                "wait": wait,
            },
        )

        # Step 1: Extract
        typer.echo("Step 1: Extracting data from Snowflake to S3...")
        extract_result = extract_data(settings, dry_run=dry_run)

        if not extract_result.success:
            typer.echo(f"Error extracting data: {extract_result.error_message}", err=True)
            raise typer.Exit(1)

        typer.echo(
            f"Successfully extracted {extract_result.record_count} records to {extract_result.output_path}"
        )

        # Step 2: Process
        typer.echo("Step 2: Processing data through AWS Entity Resolution...")
        process_result = process_data(
            settings,
            dry_run=dry_run,
            wait=wait,
        )

        if not process_result.success:
            typer.echo(f"Error processing data: {process_result.error_message}", err=True)
            raise typer.Exit(1)

        typer.echo(f"Successfully processed data: {process_result.output_path}")

        # Step 3: Load
        typer.echo("Step 3: Loading matched records to Snowflake...")
        load_result = load_records(
            settings,
            s3_key=process_result.output_path.split("/")[-1]
            if process_result.output_path
            else None,
            dry_run=dry_run,
        )

        if not load_result.success:
            typer.echo(f"Error loading data: {load_result.error_message}", err=True)
            raise typer.Exit(1)

        typer.echo(
            f"Successfully loaded {load_result.record_count} records to {settings.target_table}"
        )

        # Pipeline complete
        typer.echo("Pipeline execution completed successfully!")
        if dry_run:
            typer.echo("This was a dry run. No data was actually processed.")

        return 0  # Return success code

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (default: .env)"
    ),
) -> None:
    """AWS Entity Resolution pipeline for creating golden records from Snowflake data."""
    # Configure logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load environment variables from config file if specified
    if config:
        load_dotenv(config)
    else:
        load_dotenv()  # Default .env file


if __name__ == "__main__":
    app()
