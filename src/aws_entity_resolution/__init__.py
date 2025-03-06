"""AWS Entity Resolution package for matching and processing entity data."""

from aws_entity_resolution.config.unified import (
    AWSConfig,
    EntityResolutionConfig,
    Environment,
    S3Config,
    Settings,
    SnowflakeConfig,
    create_settings,
    get_settings,
)

__all__ = [
    "AWSConfig",
    "EntityResolutionConfig",
    "Environment",
    "S3Config",
    "Settings",
    "SnowflakeConfig",
    "create_settings",
    "get_settings",
]
