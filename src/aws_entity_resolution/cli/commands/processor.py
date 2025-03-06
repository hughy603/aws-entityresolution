"""Processor commands for Entity Resolution.

This module provides commands for processing data with AWS Entity Resolution.
"""

import typer

from aws_entity_resolution.cli.commands.base import BaseCommand, CommandResult, command_callback
from aws_entity_resolution.processor.processor import process_data as process_data_internal
from aws_entity_resolution.processor.types import ProcessResult

app = typer.Typer(help="Process entity data with AWS Entity Resolution")


class ProcessCommand(BaseCommand[ProcessResult]):
    """Command for processing data with AWS Entity Resolution."""

    def execute(
        self,
        input_path: str,
        output_prefix: str = "output/",
        wait: bool = True,
        timeout: int = 3600,
    ) -> CommandResult[ProcessResult]:
        """Process data with AWS Entity Resolution.

        Args:
            input_path: S3 path to input data (relative to bucket)
            output_prefix: S3 prefix for output data
            wait: Whether to wait for processing to complete
            timeout: Maximum time to wait in seconds

        Returns:
            Command result with processing output
        """
        # Validate required settings
        validation = self.validate_settings(["s3.bucket", "entity_resolution.workflow_id"])
        if not validation.success:
            return validation

        # Log the processing parameters
        self.log_start(
            "process_start",
            {
                "input_path": input_path,
                "output_prefix": output_prefix,
                "wait": wait,
                "timeout": timeout,
            },
        )

        try:
            # Process the data
            result = process_data_internal(
                self.settings,
                input_path=input_path,
                output_prefix=output_prefix,
                wait=wait,
                timeout=timeout,
            )

            if result.success:
                message = ""
                if wait:
                    message = (
                        f"Successfully processed data. Results available at: {result.output_path}"
                    )
                else:
                    message = (
                        f"Processing started with job ID: {result.job_id}. "
                        f"Results will be available at: {result.output_path}"
                    )

                return CommandResult(success=True, result=result, error_message=message)
            return CommandResult(
                success=False,
                error_message=result.error_message or "Unknown error",
            )
        except Exception as e:
            return CommandResult(success=False, error_message=str(e), exit_code=1)


class StatusCommand(BaseCommand[ProcessResult]):
    """Command for checking Entity Resolution job status."""

    def execute(self, job_id: str) -> CommandResult[ProcessResult]:
        """Check the status of an Entity Resolution job.

        Args:
            job_id: Entity Resolution job ID to check

        Returns:
            Command result with job status
        """
        # Validate required settings
        validation = self.validate_settings(["s3.bucket", "entity_resolution.workflow_id"])
        if not validation.success:
            return validation

        try:
            # Get the job status
            result = process_data_internal(
                self.settings,
                job_id=job_id,
                check_status_only=True,
            )

            if result.success:
                message = f"Job status: {result.status}"
                if result.status == "COMPLETED":
                    message += f"\nResults available at: {result.output_path}"

                return CommandResult(success=True, result=result, error_message=message)
            return CommandResult(
                success=False,
                error_message=result.error_message or "Unknown error",
            )
        except Exception as e:
            return CommandResult(success=False, error_message=str(e), exit_code=1)


@app.command("run")
def process(
    input_path: str = typer.Argument(
        ...,
        help="S3 path to input data (relative to bucket, e.g., 'data/input.csv')",
    ),
    output_prefix: str = typer.Option(
        "output/",
        "--output-prefix",
        "-o",
        help="S3 prefix for output data",
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for processing to complete"),
    timeout: int = typer.Option(3600, "--timeout", "-t", help="Maximum time to wait in seconds"),
) -> None:
    """Process entity data with AWS Entity Resolution.

    This command takes input data from S3 and processes it through AWS Entity Resolution
    to identify and link matching records. The results are stored back in S3.

    Examples:
        # Process a specific input file and wait for completion
        $ aws-entity-resolution process run data/customers.csv

        # Process with a custom output location
        $ aws-entity-resolution process run data/customers.csv --output-prefix results/matched/

        # Start processing without waiting for completion
        $ aws-entity-resolution process run data/customers.csv --no-wait

        # Set a custom timeout for waiting
        $ aws-entity-resolution process run data/customers.csv --timeout 7200
    """
    callback = command_callback(ProcessCommand, ProcessCommand.execute)
    callback(
        input_path=input_path,
        output_prefix=output_prefix,
        wait=wait,
        timeout=timeout,
    )


@app.command("status")
def check_status(
    job_id: str = typer.Argument(..., help="Entity Resolution job ID to check"),
) -> None:
    """Check the status of an Entity Resolution job.

    Examples:
        $ aws-entity-resolution process status er-job-123456789
    """
    callback = command_callback(StatusCommand, StatusCommand.execute)
    callback(job_id=job_id)
