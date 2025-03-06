"""Validation utilities for the AWS Entity Resolution package."""

import re
from typing import Any, Union

from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger

logger = get_logger(__name__)


@handle_exceptions("validate_s3_path")
def validate_s3_path(path: str) -> bool:
    """Validate an S3 path format.

    Args:
        path: S3 path to validate (s3://bucket/key or bucket/key)

    Returns:
        True if valid, False otherwise
    """
    # Check if path starts with s3:// or is in bucket/key format
    s3_uri_pattern = r"^s3://([^/]+)/(.*)$"
    bucket_key_pattern = r"^([^/]+)/(.*)$"

    # Explicitly reject URLs with other protocols
    if re.match(r"^(http|https|ftp)://", path):
        return False

    # Reject malformed s3: URIs (missing double slash)
    if path.startswith("s3:") and not path.startswith("s3://"):
        return False

    return bool(re.match(s3_uri_pattern, path) or re.match(bucket_key_pattern, path))


@handle_exceptions("validate_required")
def validate_required(value: Any, name: str) -> None:
    """Validate that a required value is not None or empty.

    Args:
        value: Value to validate
        name: Name of the value for error messages

    Raises:
        ValueError: If value is None or empty
    """
    if value is None:
        msg = f"{name} is required and cannot be None"
        raise ValueError(msg)

    if isinstance(value, str) and not value.strip():
        msg = f"{name} is required and cannot be empty"
        raise ValueError(msg)

    if isinstance(value, Union[list, dict] | Union[set, tuple]) and not value:
        msg = f"{name} is required and cannot be empty"
        raise ValueError(msg)


@handle_exceptions("validate_enum")
def validate_enum(value: Any, valid_values: list[Any], name: str) -> None:
    """Validate that a value is one of the valid values.

    Args:
        value: Value to validate
        valid_values: List of valid values
        name: Name of the value for error messages

    Raises:
        ValueError: If value is not in valid_values
    """
    if value not in valid_values:
        msg = f"{name} must be one of {valid_values}, got {value}"
        raise ValueError(msg)
