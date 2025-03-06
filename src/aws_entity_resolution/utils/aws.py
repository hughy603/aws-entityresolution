"""AWS-specific utilities for the AWS Entity Resolution package."""

from typing import Any

import boto3

from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger

logger = get_logger(__name__)


@handle_exceptions("aws_client_creation")
def get_aws_client(service_name: str, region_name: str | None = None) -> Any:
    """Get an AWS service client with proper error handling.

    Args:
        service_name: Name of the AWS service
        region_name: AWS region name (optional)

    Returns:
        AWS service client
    """
    return boto3.client(service_name, region_name=region_name)


@handle_exceptions("aws_resource_creation")
def get_aws_resource(service_name: str, region_name: str | None = None) -> Any:
    """Get an AWS service resource with proper error handling.

    Args:
        service_name: Name of the AWS service
        region_name: AWS region name (optional)

    Returns:
        AWS service resource
    """
    return boto3.resource(service_name, region_name=region_name)
