"""Settings module for AWS Entity Resolution.

This module provides functions for retrieving application settings from various sources.
"""

import os
from functools import lru_cache
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from aws_entity_resolution.config.unified import (
    ConfigLoader,
    Settings,
)
from aws_entity_resolution.utils.error import ConfigError
from aws_entity_resolution.utils.logging import get_logger

logger = get_logger(__name__)


def get_password(secret_name: str | None = None, region: str = "us-east-1") -> Optional[str]:
    """Get a password from AWS Secrets Manager or environment.

    Args:
        secret_name: Name of the secret. If None, tries to get from environment.
        region: AWS region

    Returns:
        The password if found, None otherwise

    Raises:
        ConfigError: If there is an error retrieving the secret
    """
    # Try getting from environment
    env_vars = ["SNOWFLAKE_PASSWORD", "DB_PASSWORD"]
    for var in env_vars:
        env_password = os.environ.get(var)
        if env_password:
            return env_password

    # Return early if no secret_name
    if not secret_name:
        return None

    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region)

        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            return response["SecretString"]
        return None
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        msg = f"Error retrieving secret {secret_name}: {error_code} - {error_message}"
        raise ConfigError(msg) from e
    except Exception as e:
        msg = f"Unexpected error retrieving secret {secret_name}: {e}"
        raise ConfigError(msg) from e


def get_aws_ssm_parameter(
    parameter_name: str,
    region: str = "us-east-1",
    is_secure: bool = False,
) -> str:
    """Get a parameter from AWS SSM Parameter Store.

    Args:
        parameter_name: Name of the parameter to retrieve
        region: AWS region
        is_secure: Whether the parameter is a secure string

    Returns:
        Parameter value as a string
    """
    try:
        client = boto3.client("ssm", region_name=region)
        response = client.get_parameter(Name=parameter_name, WithDecryption=is_secure)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.warning(f"Failed to retrieve SSM parameter {parameter_name}: {e}")
        return ""


def get_entity_resolution_schema(schema_name: str, region: str = "us-east-1") -> dict[str, Any]:
    """Get Entity Resolution schema from AWS.

    Args:
        schema_name: Name of the schema to retrieve
        region: AWS region

    Returns:
        Schema definition as a dictionary
    """
    try:
        client = boto3.client("entityresolution", region_name=region)
        response = client.get_schema(schemaName=schema_name)

        attributes = []
        for attr in response.get("attributes", []):
            attributes.append(
                {
                    "name": attr.get("name"),
                    "type": attr.get("type"),
                    "subtype": attr.get("subType", "NONE"),
                    "match_key": attr.get("matchKey", False),
                }
            )

        return {
            "schema_name": schema_name,
            "schema_arn": response.get("schemaArn", ""),
            "attributes": attributes,
        }
    except Exception as e:
        logger.warning(f"Failed to retrieve schema {schema_name} from AWS: {e}")
        return {
            "schema_name": schema_name,
            "schema_arn": "",
            "attributes": [],
        }


@lru_cache
def create_settings(
    env_prefix: str = "",
    config_file: Optional[str] = None,
    aws_secrets_name: Optional[str] = None,
    aws_region: str = "us-east-1",
) -> Settings:
    """Create Settings from various sources.

    This function loads settings from:
    1. Environment variables
    2. Configuration file
    3. AWS Secrets Manager
    4. System defaults

    Args:
        env_prefix: Optional prefix for environment variables
        config_file: Optional path to a configuration file
        aws_secrets_name: Optional name of an AWS secret
        aws_region: AWS region for AWS services

    Returns:
        Settings instance
    """
    # Create config loader
    loader = ConfigLoader()

    # Load from environment variables
    env_config = loader.load_from_env(env_prefix)

    # Load from file if specified
    file_config = {}
    if config_file:
        try:
            file_config = loader.load_from_file(config_file)
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Failed to load configuration from file: {e}")

    # Load from AWS Secrets Manager if specified
    secrets_config = {}
    if aws_secrets_name:
        try:
            secrets_config = loader.load_from_aws_secrets(
                aws_secrets_name,
                region=aws_region,
            )
        except Exception as e:
            logger.warning(f"Failed to load configuration from AWS Secrets Manager: {e}")

    # Merge configurations with precedence: env > file > secrets > defaults
    merged_config = loader.merge_configs(secrets_config, file_config, env_config)

    try:
        # Create Settings instance from merged configuration
        settings = Settings(**merged_config)

        # Check if we need to fetch Entity Resolution schema from AWS
        er_config = settings.entity_resolution
        if er_config.schema_name and not er_config.attributes:
            schema_data = get_entity_resolution_schema(
                er_config.schema_name,
                region=settings.aws.region,
            )
            if schema_data.get("attributes"):
                logger.info(f"Fetched schema {er_config.schema_name} from AWS")
                # This will trigger the model validator to populate attributes
                settings.entity_resolution.fetch_schema_from_aws()

        return settings
    except ValidationError as e:
        logger.exception(f"Failed to validate settings: {e}")
        # Return default settings if validation fails
        return Settings()


@lru_cache
def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings instance
    """
    # Load config file from environment variable or default path
    config_file = os.environ.get(
        "CONFIG_FILE",
        os.environ.get("AWS_ENTITY_RESOLUTION_CONFIG", "config.yaml"),
    )

    # Load AWS secret name from environment variable
    aws_secrets_name = os.environ.get("AWS_SECRETS_NAME")

    # Load AWS region from environment variable or default
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    # Create settings with optimal configuration
    return create_settings(
        config_file=config_file,
        aws_secrets_name=aws_secrets_name,
        aws_region=aws_region,
    )


def refresh_settings() -> None:
    """Refresh cached settings."""
    get_settings.cache_clear()
    create_settings.cache_clear()


def get_aws_client(service_name: str, region: Optional[str] = None) -> Any:
    """Get an AWS service client with the correct configuration.

    Args:
        service_name: Name of the AWS service
        region: Optional region override

    Returns:
        Boto3 service client
    """
    settings = get_settings()
    aws_config = settings.aws

    client_kwargs = {
        "region_name": region or aws_config.region,
    }

    if aws_config.profile:
        session = boto3.Session(profile_name=aws_config.profile)
        return session.client(service_name, **client_kwargs)

    return boto3.client(service_name, **client_kwargs)
