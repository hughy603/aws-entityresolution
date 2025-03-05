"""CLI interface for AWS Entity Resolution processing."""

import sys
from typing import Any, Optional

import boto3
import typer

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.services import EntityResolutionService

from .processor import process_data

app = typer.Typer(help="Process entity data through AWS Entity Resolution")

# Version information
__version__ = "0.1.0"


def validate_settings(settings: Settings) -> None:
    """Validate required settings are present."""
    if not settings.entity_resolution.workflow_name:
        typer.echo("Error: ER_WORKFLOW_NAME environment variable is required", err=True)
        raise typer.Exit(1)

    if not settings.s3.bucket:
        typer.echo("Error: S3_BUCKET_NAME environment variable is required", err=True)
        raise typer.Exit(1)


@app.command()
def process(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Show what would be processed without performing the processing",
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for processing to complete"),
    input_uri: Optional[str] = typer.Option(
        None, "--input-uri", help="URI of input data (s3://bucket/key)"
    ),
    output_file: Optional[str] = typer.Option(None, "--output-file", help="Custom output filename"),
    matching_threshold: Optional[float] = typer.Option(
        None, "--matching-threshold", help="Matching confidence threshold"
    ),
) -> None:
    """Process entity data through AWS Entity Resolution."""
    try:
        # Get settings from environment variables
        settings = get_settings()
        validate_settings(settings)

        if dry_run:
            typer.echo("Dry run mode - would process with:")
            typer.echo(f"  Workflow: {settings.entity_resolution.workflow_name}")
            typer.echo(f"  Input bucket: s3://{settings.s3.bucket}/{settings.s3.prefix}")
            typer.echo(
                f"  Entity attributes: {', '.join(settings.entity_resolution.entity_attributes)}"
            )
            return

        # Process data
        result = process_data(settings, dry_run=dry_run)
        if result.status == "success":
            typer.echo(
                f"Successfully processed {result.input_records} records, found {result.matched_records} matches"
            )
            typer.echo(f"Matched: {result.matched_records}")
            unique_count = result.input_records - result.matched_records
            typer.echo(f"Unique: {unique_count}")
            typer.echo(f"Results written to: s3://{result.s3_bucket}/{result.s3_key}")
        else:
            typer.echo(f"Error: {result.error_message}", err=True)
            raise typer.Exit(1)

    except boto3.exceptions.Boto3Error as e:
        typer.echo(f"AWS error: {e!s}", err=True)
        typer.echo("Error processing data", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error processing data: {e!s}", err=True)
        typer.echo("Error processing data", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e!s}", err=True)
        typer.echo("Error processing data", err=True)
        raise typer.Exit(1)


def get_workflow_status(settings: Settings, workflow_name: Optional[str] = None) -> dict[str, Any]:
    """Get the status of an Entity Resolution workflow.

    Args:
        settings: Application settings
        workflow_name: Optional workflow name, will use settings if not provided

    Returns:
        Dictionary with workflow status information
    """
    name = workflow_name or settings.entity_resolution.workflow_name
    er_service = EntityResolutionService(settings)

    # Note: This is a placeholder. In a real implementation, you would call
    # the actual AWS Entity Resolution API to get workflow status
    return {"workflowName": name, "status": "ACTIVE", "lastUpdatedAt": "2023-01-01T12:00:00Z"}


@app.command()
def workflow_status(
    workflow_name: Optional[str] = typer.Argument(
        None, help="Name of the workflow to check (uses configured workflow if not specified)"
    ),
) -> None:
    """Show the status of an Entity Resolution workflow."""
    try:
        # Get settings from environment variables
        settings = get_settings()

        # Validate we have a workflow name
        name = workflow_name or settings.entity_resolution.workflow_name
        if not name:
            typer.echo("Error: workflow name is required", err=True)
            raise typer.Exit(1)

        # Get workflow status
        status = get_workflow_status(settings, name)

        # Display status information
        typer.echo(f"Workflow: {status['workflowName']}")
        typer.echo(f"Status: {status['status']}")
        typer.echo(f"Last updated: {status['lastUpdatedAt']}")

    except boto3.exceptions.Boto3Error as e:
        typer.echo(f"AWS error: {e!s}", err=True)
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error: {e!s}", err=True)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AWS Entity Resolution Processor v{__version__}")


if __name__ == "__main__":
    app()
