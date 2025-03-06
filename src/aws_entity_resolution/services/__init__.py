"""Service classes for AWS Entity Resolution.

This package provides service classes for interacting with AWS services and Snowflake.
Each service class follows a consistent pattern and uses dependency injection for configuration.
"""

from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.s3 import S3Service
from aws_entity_resolution.services.snowflake import SnowflakeService

__all__ = [
    "EntityResolutionService",
    "S3Service",
    "SnowflakeService",
]
