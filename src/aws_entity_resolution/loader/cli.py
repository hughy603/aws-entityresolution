from typing import Optional

"""CLI interface for the loader module."""

import sys

import boto3
import snowflake.connector
import typer

from aws_entity_resolution.config import get_settings
from aws_entity_resolution.loader.loader import LoadingResult, create_target_table, load_records
from aws_entity_resolution.services import SnowflakeService
from aws_entity_resolution.utils import get_logger, log_event

app = typer.Typer(help="Load matched records from S3 to Snowflake")

# Version information
__version__ = "0.1.0"


def validate_settings() -> None:
    """Validate required environment variables are set."""
    try:
        settings = get_settings()
        required_vars: list[tuple[str, str]] = [
            ("S3_BUCKET_NAME", settings.s3.bucket),
            ("SNOWFLAKE_ACCOUNT", settings.snowflake_target.account),
            ("SNOWFLAKE_USERNAME", settings.snowflake_target.username),
            ("SNOWFLAKE_PASSWORD", settings.snowflake_target.password),
            ("SNOWFLAKE_ROLE", settings.snowflake_target.role),
            ("SNOWFLAKE_WAREHOUSE", settings.snowflake_target.warehouse),
            ("SNOWFLAKE_TARGET_DATABASE", settings.snowflake_target.database),
            ("SNOWFLAKE_TARGET_SCHEMA", settings.snowflake_target.schema),
            ("TARGET_TABLE", settings.target_table),
        ]

        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

        if missing_vars:
            typer.echo(
                f"Missing required environment variables: {', '.join(missing_vars)}",
                err=True,
            )
            raise typer.Exit(1)
    except (ValueError, TypeError) as e:
        typer.echo(f"Error loading settings: {e!s}", err=True)
        raise typer.Exit(1)


@app.command()
def load(
    s3_key: Optional[str] = typer.Argument(None, help="S3 key containing matched records"),
    input_uri: Optional[str] = typer.Option(
        None, "--input-uri", help="URI of input data (s3://bucket/key)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be loaded without actually loading"
    ),
    target_table: Optional[str] = typer.Option(
        None, "--target-table", help="Override target table name"
    ),
    truncate_target: bool = typer.Option(
        False, "--truncate-target", help="Truncate target table before loading"
    ),
) -> None:
    """Load matched records from S3 to Snowflake."""
    try:
        # Validate settings
        validate_settings()
        settings = get_settings()

        # Process input_uri if provided
        if input_uri and not s3_key:
            if input_uri.startswith("s3://"):
                # Extract the key part from s3://bucket/key
                parts = input_uri.replace("s3://", "").split("/", 1)
                if len(parts) > 1:
                    s3_key = parts[1]

        # Ensure we have a key
        if not s3_key:
            typer.echo("Error: S3 key is required", err=True)
            raise typer.Exit(1)

        if dry_run:
            typer.echo("Dry run mode - showing configuration:")
            typer.echo(f"  S3 Bucket: {settings.s3.bucket}")
            typer.echo(f"  S3 Key: {s3_key}")
            typer.echo(f"  Target Database: {settings.snowflake_target.database}")
            typer.echo(f"  Target Schema: {settings.snowflake_target.schema}")
            typer.echo(f"  Target Table: {settings.target_table}")
            return

        # Load records
        typer.echo("Loading matched records to Snowflake...")
        result = load_data(settings, s3_key)

        if result.status == "success":
            typer.echo(
                f"Successfully loaded {result.records_loaded} records to {result.target_table}"
            )
            typer.echo(f"Target table: {result.target_table}")
            if hasattr(result, "execution_time") and result.execution_time is not None:
                typer.echo(f"execution time: {result.execution_time}s")
            if result.error_message:
                typer.echo(f"Note: {result.error_message}")
        else:
            typer.echo(f"Failed to load records: {result.error_message}", err=True)
            raise typer.Exit(1)
    except (
        snowflake.connector.errors.ProgrammingError,
        snowflake.connector.errors.DatabaseError,
    ) as e:
        typer.echo(f"Database error: {e!s}", err=True)
        raise typer.Exit(1)
    except boto3.exceptions.Boto3Error as e:
        typer.echo(f"AWS error: {e!s}", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error loading data: {e!s}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error loading data: {e!s}", err=True)
        raise typer.Exit(1)


def load_data(settings, s3_key: Optional[str] = None) -> LoadingResult:
    """Load data from S3 to Snowflake.

    This function is a wrapper around load_records for testing purposes.

    Args:
        settings: Application settings
        s3_key: Optional S3 key containing matched records

    Returns:
        LoadingResult with status and metadata
    """
    return load_records(settings, s3_key)


@app.command()
def create_table() -> None:
    """Create the target table in Snowflake if it doesn't exist."""
    try:
        # Validate settings
        validate_settings()
        settings = get_settings()

        # Create Snowflake service
        snowflake_service = SnowflakeService(settings, use_target=True)

        # Create table
        typer.echo(f"Creating table {settings.target_table} if not exists...")
        create_target_table(snowflake_service, settings)
        typer.echo("Successfully created target table")
    except (
        snowflake.connector.errors.ProgrammingError,
        snowflake.connector.errors.DatabaseError,
    ) as e:
        typer.echo(f"Database error: {e!s}", err=True)
        typer.echo("Error creating target table", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error creating target table: {e!s}", err=True)
        typer.echo("Error creating target table", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e!s}", err=True)
        typer.echo("Error creating target table", err=True)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AWS Entity Resolution Loader v{__version__}")


if __name__ == "__main__":
    app()
