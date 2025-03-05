"""CLI interface for AWS Entity Resolution processing."""

import sys
from typing import Any, Optional

import boto3
import typer

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.services import EntityResolutionService
from aws_entity_resolution.utils import get_logger, log_event

from .processor import process_data

app = typer.Typer(help="Process entity data through AWS Entity Resolution")
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

    if not settings.entity_resolution.workflow_name:
        missing.append("ER_WORKFLOW_NAME")

    if not settings.s3.bucket:
        missing.append("S3_BUCKET_NAME")

    if missing:
        typer.echo(f"Error: Missing required environment variables: {', '.join(missing)}", err=True)
        return False
    return True


@app.command("run")
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

        if not validate_settings(settings):
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
        else:
            typer.echo(f"Error processing data: {result.error_message}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(1)


def get_workflow_status(settings: Settings, workflow_name: Optional[str] = None) -> dict[str, Any]:
    """Get the status of an Entity Resolution workflow.

    Args:
        settings: Application settings
        workflow_name: Name of the workflow to check (uses configured workflow if not specified)

    Returns:
        dict: Workflow status information
    """
    workflow = workflow_name or settings.entity_resolution.workflow_name
    if not workflow:
        raise ValueError("Workflow name is required")

    service = EntityResolutionService(settings)
    return service.get_workflow_status(workflow)


@app.command()
def workflow_status(
    workflow_name: Optional[str] = typer.Argument(
        None, help="Name of the workflow to check (uses configured workflow if not specified)"
    ),
) -> None:
    """Check the status of an Entity Resolution workflow."""
    try:
        settings = get_settings()

        if not settings.entity_resolution.workflow_name and not workflow_name:
            typer.echo(
                "Error: Workflow name is required. Specify with ER_WORKFLOW_NAME or --workflow-name",
                err=True,
            )
            raise typer.Exit(1)

        status = get_workflow_status(settings, workflow_name)

        typer.echo(f"Workflow: {workflow_name or settings.entity_resolution.workflow_name}")
        typer.echo(f"Status: {status.get('workflowStatus', 'Unknown')}")

        if "statistics" in status:
            stats = status["statistics"]
            typer.echo("\nStatistics:")
            for key, value in stats.items():
                typer.echo(f"  {key}: {value}")

    except Exception as e:
        typer.echo(f"Error checking workflow status: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AWS Entity Resolution Processor v{__version__}")


if __name__ == "__main__":
    app()
