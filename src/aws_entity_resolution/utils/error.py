"""Error handling utilities for the AWS Entity Resolution package."""

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

from aws_entity_resolution.utils.logging import get_logger

# Type variable for function type hints
F = TypeVar("F", bound=Callable[..., Any])

# Create a logger instance
logger = get_logger(__name__)


class BaseError(Exception):
    """Base error class for AWS Entity Resolution."""

    def __init__(self, message: str) -> None:
        """Initialize the error.

        Args:
            message: Error message
        """
        super().__init__(message)
        self.message = message


class ServiceError(BaseError):
    """Error raised by service classes."""


class ConfigError(BaseError):
    """Error raised by configuration classes."""


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
                logger.exception(
                    json.dumps(
                        {
                            "message": f"Error in {operation_name}",
                            "error": str(e),
                            "error_type": e.__class__.__name__,
                        },
                    ),
                )
                raise
            except Exception as e:  # Catch any other exceptions not explicitly handled
                logger.critical(
                    json.dumps(
                        {
                            "message": f"Unexpected error in {operation_name}",
                            "error": str(e),
                            "error_type": e.__class__.__name__,
                            "severity": "CRITICAL",
                        },
                    ),
                )
                raise

        return wrapper  # type: ignore

    return decorator
