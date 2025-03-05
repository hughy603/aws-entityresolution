"""CLI interface for the extractor module."""

from typing import Optional

import typer

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.extractor.extractor import extract_data
from aws_entity_resolution.utils import get_logger, log_event

app = typer.Typer(help="Extract entity data from Snowflake to S3")
logger = get_logger(__name__)


def validate_settings(settings: Optional[Settings] = None) -> bool:
    """Validate required settings are present.

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


@app.command("run")
def extract(
    source_table: Optional[str] = typer.Option(
        None,
        "--source-table",
        "-t",
        help="Override source table name from environment variable",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Custom SQL query to extract data (overrides source table)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Show what would be extracted without performing the extraction",
    ),
) -> None:
    """Extract entity data from Snowflake to S3."""
    settings = get_settings()

    if not validate_settings(settings):
        raise typer.Exit(1)

    # Override source table if provided
    if source_table:
        settings.source_table = source_table

    try:
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


if __name__ == "__main__":
    app()
