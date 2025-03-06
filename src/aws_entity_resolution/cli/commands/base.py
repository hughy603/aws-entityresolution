"""Base command structure for CLI commands.

This module provides base classes and utilities for CLI commands,
ensuring consistent behavior and error handling across all commands.
"""

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, Optional, TypeVar

import typer
from pydantic import ValidationError

from aws_entity_resolution.config import Settings, get_settings
from aws_entity_resolution.utils.logging import get_logger, log_event

# Type variable for the result of a command
T = TypeVar("T")

# Logger for this module
logger = get_logger(__name__)


class CommandResult(Generic[T]):
    """Result of a command execution."""

    def __init__(
        self: "CommandResult[T]",
        success: bool,
        result: Optional[T] = None,
        error_message: str = "",
        exit_code: int = 0,
    ) -> None:
        """Initialize a command result.

        Args:
            success: Whether the command was successful
            result: The result of the command
            error_message: Error message if the command failed
            exit_code: Exit code if the command failed
        """
        self.success = success
        self.result = result
        self.error_message = error_message
        self.exit_code = exit_code


class BaseCommand(ABC, Generic[T]):
    """Base class for all commands."""

    def __init__(self: "BaseCommand[T]", settings: Optional[Settings] = None) -> None:
        """Initialize a command.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or get_settings()
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def execute(self: "BaseCommand[T]", **kwargs: Any) -> CommandResult[T]:
        """Execute the command.

        Args:
            **kwargs: Command-specific arguments

        Returns:
            Command result
        """

    def validate_settings(
        self: "BaseCommand[T]",
        required_settings: list[str],
    ) -> CommandResult[None]:
        """Validate required settings are present.

        Args:
            required_settings: List of setting paths (e.g., "s3.bucket")

        Returns:
            Command result indicating success or failure
        """
        missing = []

        for path in required_settings:
            parts = path.split(".")
            value = self.settings
            for part in parts:
                if not hasattr(value, part):
                    missing.append(path)
                    break
                value = getattr(value, part)
                if value is None or value == "":
                    missing.append(path)
                    break

        if missing:
            return CommandResult(
                success=False,
                error_message=f"Missing required settings: {', '.join(missing)}",
                exit_code=1,
            )
        return CommandResult(success=True)

    def log_start(
        self: "BaseCommand[T]",
        event_name: str,
        details: dict[str, Any],
    ) -> None:
        """Log the start of a command execution.

        Args:
            event_name: Name of the event
            details: Event details
        """
        log_event(event_name, **details)


def command_callback(
    cmd_class: type[BaseCommand[T]],
    cmd_func: Callable[..., CommandResult[T]],
) -> Callable[..., None]:
    """Create a callback function for a typer command.

    This function wraps a command execution function with standard error handling,
    providing consistent behavior across all commands.

    Args:
        cmd_class: Command class to instantiate
        cmd_func: Command function to call

    Returns:
        Typer callback function
    """

    def callback(**kwargs: Any) -> None:
        """Typer callback function.

        Args:
            **kwargs: Command arguments

        Raises:
            typer.Exit: If the command fails
        """
        try:
            # Create command instance
            cmd = cmd_class()

            # Execute command
            result = cmd_func(cmd, **kwargs)

            # Handle result
            if result.success:
                if result.result is not None:
                    typer.echo(str(result.result))
            else:
                typer.echo(f"Error: {result.error_message}", err=True)
                raise typer.Exit(result.exit_code)

        except ValidationError as e:
            typer.echo(f"Validation error: {e}", err=True)
            raise typer.Exit(1) from e
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RuntimeError,
            ConnectionError,
            OSError,
            ImportError,
        ) as e:
            typer.echo(f"Error: {e!s}", err=True)
            raise typer.Exit(1) from e
        except Exception as e:
            typer.echo(f"Unexpected critical error: {e!s}", err=True)
            logger.critical(
                json.dumps(
                    {
                        "message": "Unexpected CLI command error",
                        "error": str(e),
                        "error_type": e.__class__.__name__,
                        "severity": "CRITICAL",
                    },
                ),
            )
            raise typer.Exit(2) from e

    return callback
