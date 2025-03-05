"""CLI interface for the loader module."""

import sys
from typing import Optional

import boto3
import snowflake.connector
import typer

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.loader.loader import LoadingResult, create_target_table, load_records
from aws_entity_resolution.services import SnowflakeService
from aws_entity_resolution.utils import get_logger, log_event

app = typer.Typer(help="Load matched records from S3 to Snowflake")
logger = get_logger(__name__)

# Version information
__version__ = "0.1.0"


def validate_settings(settings: Optional[Settings] = None) -> bool:
    """Validate required settings are present.

    Returns:
        bool: True if settings are valid, False otherwise.
    """
    if settings is None:
        settings = get_settings()

    missing = []

    if not settings.s3.bucket:
        missing.append("S3_BUCKET_NAME")

    if not settings.snowflake_target.account:
        missing.append("SNOWFLAKE_ACCOUNT")

    if not settings.snowflake_target.username:
        missing.append("SNOWFLAKE_USERNAME")

    if not settings.snowflake_target.password:
        missing.append("SNOWFLAKE_PASSWORD")

    if not settings.snowflake_target.warehouse:
        missing.append("SNOWFLAKE_WAREHOUSE")

    if not settings.snowflake_target.database:
        missing.append("SNOWFLAKE_TARGET_DATABASE")

    if not settings.snowflake_target.schema:
        missing.append("SNOWFLAKE_TARGET_SCHEMA")

    if not settings.target_table:
        missing.append("TARGET_TABLE")

    if missing:
        typer.echo(f"Error: Missing required environment variables: {', '.join(missing)}", err=True)
        return False
    return True


@app.command("run")
def load(
    s3_key: Optional[str] = typer.Option(
        None, "--s3-key", "-k", help="S3 key containing matched records"
    ),
    input_uri: Optional[str] = typer.Option(
        None, "--input-uri", "-i", help="URI of input data (s3://bucket/key)"
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
) -> None:
    """Load matched records from S3 to Snowflake."""
    try:
        settings = get_settings()

        if not validate_settings(settings):
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
                "s3_key": s3_key or input_uri,
                "target_table": settings.target_table,
                "dry_run": dry_run,
                "truncate": truncate_target,
            },
        )

        # Determine the S3 key to use
        if input_uri and not s3_key:
            # Extract bucket and key from input_uri (s3://bucket/key)
            if input_uri.startswith("s3://"):
                parts = input_uri[5:].split("/", 1)
                if len(parts) == 2:
                    s3_key = parts[1]

        # Load the data
        result = load_records(
            settings,
            s3_key=s3_key,
            dry_run=dry_run,
            truncate=truncate_target,
        )

        if result.success:
            typer.echo(
                f"Successfully loaded {result.record_count} records to {settings.target_table}"
            )
            if dry_run:
                typer.echo("This was a dry run. No data was actually loaded.")
        else:
            typer.echo(f"Error loading data: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def create_table(
    target_table: Optional[str] = typer.Option(
        None, "--target-table", "-t", help="Override target table name"
    ),
    if_not_exists: bool = typer.Option(
        True, "--if-not-exists/--replace", help="Create table only if it doesn't exist"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show SQL without executing"),
) -> None:
    """Create the target table in Snowflake."""
    try:
        settings = get_settings()

        if not validate_settings(settings):
            raise typer.Exit(1)

        # Override target table if provided
        if target_table:
            settings.target_table = target_table

        # Log the table creation parameters
        log_event(
            logger,
            "Creating target table",
            {
                "target_table": settings.target_table,
                "if_not_exists": if_not_exists,
                "dry_run": dry_run,
            },
        )

        # Create the table
        result = create_target_table(
            settings,
            if_not_exists=if_not_exists,
            dry_run=dry_run,
        )

        if result.success:
            typer.echo(f"Successfully created table {settings.target_table}")
            if dry_run:
                typer.echo("This was a dry run. SQL was not executed.")
                typer.echo(f"SQL: {result.sql}")
        else:
            typer.echo(f"Error creating table: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AWS Entity Resolution Loader v{__version__}")


if __name__ == "__main__":
    app()
