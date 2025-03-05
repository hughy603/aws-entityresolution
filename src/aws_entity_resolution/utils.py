"""Shared utility functions for the AWS Entity Resolution pipeline."""

import functools
import json
import logging
import os
import sys
from collections.abc import Callable
from typing import Any, Dict, TypeVar

# Type variable for function type hints
F = TypeVar("F", bound=Callable[..., Any])


# Configure structured logging
def setup_structured_logging() -> logging.Logger:
    """Set up structured logging for Splunk integration.

    Returns:
        Configured logger instance
    """
    # Get logger
    logger = logging.getLogger(__name__)

    # Configure handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        # Format as JSON for Splunk
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", %(message)s}'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    # Set level from environment or default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level))

    return logger


# Create a logger
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Module name for the logger

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Set level from environment or default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level))

    return logger


# Create a logger instance
logger = get_logger(__name__)


def log_event(logger: logging.Logger, event_name: str, event_data: dict[str, Any]) -> None:
    """Log a structured event.

    Args:
        logger: Logger instance
        event_name: Name of the event
        event_data: Event data
    """
    # Create a safe copy of the event data with primitive types
    safe_data = {}
    for key, value in event_data.items():
        # Convert to primitive types to ensure JSON serialization
        if hasattr(value, "__class__") and value.__class__.__name__ == "MagicMock":
            safe_data[key] = str(value)
        else:
            try:
                # Try to convert to a simple type
                json.dumps({key: value})
                safe_data[key] = value
            except (TypeError, OverflowError):
                # If it can't be serialized, convert to string
                safe_data[key] = str(value)

    log_data = {
        "event": event_name,
        **safe_data,
    }

    logger.info(json.dumps(log_data))


def handle_exceptions(operation_name: str) -> Callable[[F], F]:
    """Decorator to handle exceptions in functions.

    Args:
        operation_name: Name of the operation for logging

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    json.dumps(
                        {
                            "message": f"Error in {operation_name}",
                            "error": str(e),
                            "error_type": e.__class__.__name__,
                        }
                    )
                )
                raise

        return wrapper  # type: ignore

    return decorator
