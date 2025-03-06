"""Configuration module for AWS Entity Resolution.

This module provides configuration classes and utilities for the AWS Entity Resolution package.
It uses Pydantic for configuration validation and environment variable loading.
"""

from aws_entity_resolution.config.unified import (
    AWSConfig,
    EntityResolutionAttributeConfig,
    EntityResolutionConfig,
    Environment,
    LogLevel,
    PipelineConfig,
    S3Config,
    Settings,
    SnowflakeConfig,
    create_settings,
    get_settings,
)

__all__ = [
    "AWSConfig",
    "EntityResolutionAttributeConfig",
    "EntityResolutionConfig",
    "Environment",
    "LogLevel",
    "PipelineConfig",
    "S3Config",
    "Settings",
    "SnowflakeConfig",
    "create_settings",
    "get_settings",
]
