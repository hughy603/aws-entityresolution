"""Logging utilities for the AWS Entity Resolution package."""

import json
import logging
import os
import sys
from typing import Any


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
            '{"timestamp":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", %(message)s}',
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    # Set level from environment or default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level))

    return logger


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


def log_event(event_name: str, **event_data: Any) -> None:
    """Log a structured event.

    Args:
        event_name: Name of the event
        **event_data: Event data as keyword arguments
    """
    logger = logging.getLogger("aws_entity_resolution")

    # Format the event data
    event_message = f'"event": "{event_name}"'

    # Add any additional data
    if event_data:
        for key, value in event_data.items():
            if isinstance(value, dict):
                value = json.dumps(value, default=str)
            else:
                value = json.dumps(value, default=str)
            event_message += f', "{key}": {value}'

    # Log the event
    logger.info(event_message)
