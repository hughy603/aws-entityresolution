"""Loader commands for Entity Resolution.

This module provides commands for loading processed data from Entity Resolution to Snowflake.
"""

from typing import Optional

import typer

from aws_entity_resolution.cli.commands.base import BaseCommand, CommandResult, command_callback
from aws_entity_resolution.loader.loader import load_records as load_records_internal
from aws_entity_resolution.loader.types import LoadResult

app = typer.Typer(help="Load processed entity data to Snowflake")


class LoadCommand(BaseCommand[LoadResult]):
    """Command for loading processed data to Snowflake."""

    def execute(
        self,
        input_path: str,
        target_table: Optional[str] = None,
        truncate: bool = False,
    ) -> CommandResult[LoadResult]:
        """Load processed entity data to Snowflake.

        Args:
            input_path: S3 path to processed data (relative to bucket)
            target_table: Override target table name from settings
            truncate: Whether to truncate target table before loading

        Returns:
            Command result with loading status
        """
        # Override target table if provided
        if target_table:
            self.settings.target_table = target_table

        # Validate required settings
        validation = self.validate_settings(
            ["snowflake_target.account", "s3.bucket", "target_table"],
        )
        if not validation.success:
            return validation

        # Log the loading parameters
        self.log_start(
            "load_start",
            {
                "input_path": input_path,
                "target_table": self.settings.target_table,
                "truncate": truncate,
            },
        )

        try:
            # Load the data
            result = load_records_internal(
                self.settings,
                input_path=input_path,
                truncate=truncate,
            )

            if result.success:
                message = f"Successfully loaded {result.record_count} records to {self.settings.target_table}"
                return CommandResult(success=True, result=result, error_message=message)
            return CommandResult(
                success=False,
                error_message=result.error_message or "Unknown error",
            )
        except Exception as e:
            return CommandResult(success=False, error_message=str(e), exit_code=1)


class SetupCommand(BaseCommand[LoadResult]):
    """Command for setting up Snowflake table."""

    def execute(
        self,
        target_table: Optional[str] = None,
        force: bool = False,
    ) -> CommandResult[LoadResult]:
        """Set up Snowflake target table for entity resolution results.

        Args:
            target_table: Override target table name from settings
            force: Whether to force recreation of table if it exists

        Returns:
            Command result with setup status
        """
        # Override target table if provided
        if target_table:
            self.settings.target_table = target_table

        # Validate required settings
        validation = self.validate_settings(
            ["snowflake_target.account", "s3.bucket", "target_table"],
        )
        if not validation.success:
            return validation

        # Log the setup parameters
        self.log_start(
            "setup_start",
            {
                "target_table": self.settings.target_table,
                "force": force,
            },
        )

        try:
            # Set up the Snowflake table
            result = load_records_internal(self.settings, setup_only=True, force=force)

            if result.success:
                message = f"Successfully set up Snowflake table {self.settings.target_table}"
                return CommandResult(success=True, result=result, error_message=message)
            return CommandResult(
                success=False,
                error_message=result.error_message or "Unknown error",
            )
        except Exception as e:
            return CommandResult(success=False, error_message=str(e), exit_code=1)


@app.command("run")
def load(
    input_path: str = typer.Argument(
        ...,
        help="S3 path to processed data (relative to bucket, e.g., 'output/matched.csv')",
    ),
    target_table: Optional[str] = typer.Option(
        None,
        "--target-table",
        "-t",
        help="Override target table name from environment variable",
    ),
    truncate: bool = typer.Option(False, "--truncate", help="Truncate target table before loading"),
) -> None:
    """Load processed entity data to Snowflake.

    This command loads processed entity resolution data from S3 into a Snowflake table.

    Examples:
        # Load data to the default target table
        $ aws-entity-resolution load run output/matched.csv

        # Load to a specific table
        $ aws-entity-resolution load run output/matched.csv --target-table GOLDEN_CUSTOMERS

        # Truncate the table before loading
        $ aws-entity-resolution load run output/matched.csv --truncate
    """
    callback = command_callback(LoadCommand, LoadCommand.execute)
    callback(input_path=input_path, target_table=target_table, truncate=truncate)


@app.command("setup")
def setup_snowflake(
    target_table: Optional[str] = typer.Option(
        None,
        "--target-table",
        "-t",
        help="Override target table name from environment variable",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force recreation of table if it exists",
    ),
) -> None:
    """Set up Snowflake target table for entity resolution results.

    This command creates the necessary Snowflake table structure for storing
    entity resolution results.

    Examples:
        # Set up the default target table
        $ aws-entity-resolution load setup

        # Set up a specific table
        $ aws-entity-resolution load setup --target-table GOLDEN_CUSTOMERS

        # Force recreation of an existing table
        $ aws-entity-resolution load setup --force
    """
    callback = command_callback(SetupCommand, SetupCommand.execute)
    callback(target_table=target_table, force=force)
