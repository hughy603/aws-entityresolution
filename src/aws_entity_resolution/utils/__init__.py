"""Utility functions for the AWS Entity Resolution package.

This package provides utility functions organized by domain:
- logging: Logging setup and structured logging utilities
- aws: AWS-specific utility functions
- error: Error handling utilities
- validation: Input validation utilities
"""

from aws_entity_resolution.utils.aws import get_aws_client, get_aws_resource
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger, log_event, setup_structured_logging
from aws_entity_resolution.utils.validation import (
    validate_enum,
    validate_required,
    validate_s3_path,
)

__all__ = [
    "get_aws_client",
    "get_aws_resource",
    "get_logger",
    "handle_exceptions",
    "log_event",
    "setup_structured_logging",
    "validate_enum",
    "validate_required",
    "validate_s3_path",
]
