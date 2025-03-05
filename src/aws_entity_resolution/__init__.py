"""AWS Entity Resolution package for matching and processing entity data."""

from aws_entity_resolution.config import (
    EntityResolutionConfig,
    S3Config,
    Settings,
    SnowflakeConfig,
    get_settings,
)

__all__ = [
    "EntityResolutionConfig",
    "S3Config",
    "Settings",
    "SnowflakeConfig",
    "get_settings",
]
