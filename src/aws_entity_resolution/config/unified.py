"""Unified configuration system for AWS Entity Resolution.

This module provides a unified configuration system for the AWS Entity Resolution package,
with support for multiple configuration sources and strict validation.
"""

import json
import os
import pathlib
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any, Literal, Optional, TypeVar

import boto3
import yaml
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator

# Type variables for config loaders
T = TypeVar("T", bound=BaseModel)
ConfigSource = Literal["env", "file", "aws_secrets", "aws_parameter_store", "aws_s3"]


class Environment(str, Enum):
    """Environment enumeration."""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EntityResolutionAttributeConfig(BaseModel):
    """Configuration for Entity Resolution attributes.

    Note: This class is now read-only and should not be used to generate schemas.
    Schema configuration should be managed through Terraform.
    """

    name: str = Field(..., description="Attribute name")
    type: str = Field(..., description="Attribute type")
    subtype: str = Field("NONE", description="Attribute subtype")
    match_key: bool = Field(False, description="Whether this attribute is a match key")


class S3Config(BaseModel):
    """S3 configuration."""

    bucket: str = Field("", description="S3 bucket name")
    prefix: str = Field("", description="S3 prefix for all data")
    input_prefix: str = Field("input/", description="S3 prefix for input data")
    output_prefix: str = Field("output/", description="S3 prefix for output data")
    region: str = Field("us-east-1", description="S3 bucket region")


class EntityResolutionConfig(BaseModel):
    """Entity Resolution configuration.

    This class now serves as a read-only configuration container
    and no longer generates schema configuration. All schema configuration
    should be managed through Terraform.
    """

    workflow_id: str = Field("", description="Workflow ID for Entity Resolution")
    workflow_name: str = Field("", description="Workflow name from infrastructure")
    schema_name: str = Field("", description="Schema name from infrastructure")
    attributes: list[EntityResolutionAttributeConfig] = Field(
        default_factory=list,
        description="Entity Resolution attributes (read-only)",
    )
    matching_threshold: float = Field(0.9, description="Matching threshold for entity resolution")
    reconciliation_mode: str = Field(
        "SOME_PROVIDER_RULES",
        description="Reconciliation mode for entity resolution",
    )

    @model_validator(mode="after")
    def fetch_schema_from_aws(self) -> "EntityResolutionConfig":
        """Fetch schema information from AWS if available.

        This replaces the previous schema generation logic.
        """
        if self.schema_name and not self.attributes:
            try:
                import boto3

                client = boto3.client("entityresolution")
                response = client.get_schema(
                    schemaName=self.schema_name,
                )

                # Parse response and populate attributes
                for attr in response.get("attributes", []):
                    self.attributes.append(
                        EntityResolutionAttributeConfig(
                            name=attr.get("name"),
                            type=attr.get("type"),
                            subtype=attr.get("subType", "NONE"),
                            match_key=attr.get("matchKey", False),
                        ),
                    )
            except Exception:
                # Failed to fetch from AWS - leave attributes empty
                pass

        return self


class SnowflakeConfig(BaseModel):
    """Snowflake configuration."""

    account: str = Field("", description="Snowflake account identifier")
    username: str = Field("", description="Snowflake username")
    password: SecretStr = Field(SecretStr(""), description="Snowflake password")
    role: str = Field("ACCOUNTADMIN", description="Snowflake role")
    warehouse: str = Field("", description="Snowflake warehouse")
    database: str = Field("", description="Snowflake database")
    schema: str = Field("", description="Snowflake schema")
    table: str = Field("", description="Snowflake table")


class AWSConfig(BaseModel):
    """AWS configuration."""

    region: str = Field("us-east-1", description="AWS region")
    profile: Optional[str] = Field(None, description="AWS profile")
    role_arn: Optional[str] = Field(None, description="AWS role ARN to assume")


class Settings(BaseModel):
    """Application settings."""

    # General settings
    environment: Environment = Field(Environment.DEV, description="Environment")
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    aws: AWSConfig = Field(default_factory=AWSConfig, description="AWS configuration")

    # Service configurations
    s3: S3Config = Field(default_factory=S3Config, description="S3 configuration")
    entity_resolution: EntityResolutionConfig = Field(
        default_factory=EntityResolutionConfig,
        description="Entity Resolution configuration",
    )
    snowflake_source: SnowflakeConfig = Field(
        default_factory=SnowflakeConfig,
        description="Snowflake source configuration",
    )
    snowflake_target: SnowflakeConfig = Field(
        default_factory=SnowflakeConfig,
        description="Snowflake target configuration",
    )

    # Table names
    source_table: str = Field("", description="Source table name")
    target_table: str = Field("GOLDEN_ENTITY_RECORDS", description="Target table name")

    @property
    def aws_region(self) -> str:
        """Get AWS region for backward compatibility.

        Returns:
            AWS region
        """
        return self.aws.region

    @property
    def aws_access_key_id(self) -> str:
        """Get AWS access key ID from environment.

        Returns:
            AWS access key ID
        """
        return os.environ.get("AWS_ACCESS_KEY_ID", "")

    @model_validator(mode="after")
    def set_aws_region_defaults(self) -> "Settings":
        """Set AWS region defaults.

        If S3 region is not set, use the AWS region.
        """
        if self.aws.region and not self.s3.region:
            self.s3.region = self.aws.region
        return self


class PipelineConfig(BaseModel):
    """Pipeline configuration."""

    name: str = Field(..., description="Pipeline name")
    description: str = Field("", description="Pipeline description")
    enabled: bool = Field(True, description="Whether the pipeline is enabled")
    schedule: Optional[str] = Field(None, description="Pipeline schedule (cron expression)")
    timeout_minutes: int = Field(60, description="Pipeline timeout in minutes")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay_seconds: int = Field(60, description="Delay between retries in seconds")
    concurrency: int = Field(1, description="Maximum number of concurrent pipeline runs")

    @model_validator(mode="after")
    def validate_schedule(self) -> "PipelineConfig":
        """Validate the schedule if provided."""
        if self.schedule is not None and not self.schedule.strip():
            self.schedule = None
        return self


@dataclass
class ConfigLoader:
    """Configuration loader."""

    def load_from_env(self, prefix: str = "") -> dict[str, Any]:
        """Load configuration from environment variables.

        Args:
            prefix: Optional prefix for environment variables

        Returns:
            Dictionary of configuration values
        """
        result: dict[str, Any] = {}

        # General settings
        if os.environ.get(f"{prefix}ENVIRONMENT"):
            result["environment"] = os.environ[f"{prefix}ENVIRONMENT"]
        if os.environ.get(f"{prefix}LOG_LEVEL"):
            result["log_level"] = os.environ[f"{prefix}LOG_LEVEL"]

        # AWS settings
        aws_config: dict[str, Any] = {}
        if os.environ.get(f"{prefix}AWS_REGION"):
            aws_config["region"] = os.environ[f"{prefix}AWS_REGION"]
        if os.environ.get(f"{prefix}AWS_PROFILE"):
            aws_config["profile"] = os.environ[f"{prefix}AWS_PROFILE"]
        if os.environ.get(f"{prefix}AWS_ROLE_ARN"):
            aws_config["role_arn"] = os.environ[f"{prefix}AWS_ROLE_ARN"]
        if aws_config:
            result["aws"] = aws_config

        # S3 settings
        s3_config: dict[str, Any] = {}
        if os.environ.get(f"{prefix}S3_BUCKET"):
            s3_config["bucket"] = os.environ[f"{prefix}S3_BUCKET"]
        if os.environ.get(f"{prefix}S3_PREFIX"):
            s3_config["prefix"] = os.environ[f"{prefix}S3_PREFIX"]
        if os.environ.get(f"{prefix}S3_INPUT_PREFIX"):
            s3_config["input_prefix"] = os.environ[f"{prefix}S3_INPUT_PREFIX"]
        if os.environ.get(f"{prefix}S3_OUTPUT_PREFIX"):
            s3_config["output_prefix"] = os.environ[f"{prefix}S3_OUTPUT_PREFIX"]
        if os.environ.get(f"{prefix}S3_REGION"):
            s3_config["region"] = os.environ[f"{prefix}S3_REGION"]
        if s3_config:
            result["s3"] = s3_config

        # Entity Resolution settings
        er_config: dict[str, Any] = {}
        if os.environ.get(f"{prefix}ENTITY_RESOLUTION_WORKFLOW_ID"):
            er_config["workflow_id"] = os.environ[f"{prefix}ENTITY_RESOLUTION_WORKFLOW_ID"]
        if os.environ.get(f"{prefix}ENTITY_RESOLUTION_WORKFLOW_NAME"):
            er_config["workflow_name"] = os.environ[f"{prefix}ENTITY_RESOLUTION_WORKFLOW_NAME"]
        if os.environ.get(f"{prefix}ENTITY_RESOLUTION_SCHEMA_NAME"):
            er_config["schema_name"] = os.environ[f"{prefix}ENTITY_RESOLUTION_SCHEMA_NAME"]
        if os.environ.get(f"{prefix}ENTITY_RESOLUTION_MATCHING_THRESHOLD"):
            er_config["matching_threshold"] = float(
                os.environ[f"{prefix}ENTITY_RESOLUTION_MATCHING_THRESHOLD"],
            )
        if os.environ.get(f"{prefix}ENTITY_RESOLUTION_RECONCILIATION_MODE"):
            er_config["reconciliation_mode"] = os.environ[
                f"{prefix}ENTITY_RESOLUTION_RECONCILIATION_MODE"
            ]
        if er_config:
            result["entity_resolution"] = er_config

        # Snowflake source settings
        sf_source_config: dict[str, Any] = {}
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_ACCOUNT"):
            sf_source_config["account"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_ACCOUNT"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_USERNAME"):
            sf_source_config["username"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_USERNAME"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_PASSWORD"):
            sf_source_config["password"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_PASSWORD"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_ROLE"):
            sf_source_config["role"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_ROLE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_WAREHOUSE"):
            sf_source_config["warehouse"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_WAREHOUSE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_DATABASE"):
            sf_source_config["database"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_DATABASE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_SCHEMA"):
            sf_source_config["schema"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_SCHEMA"]
        if os.environ.get(f"{prefix}SNOWFLAKE_SOURCE_TABLE"):
            sf_source_config["table"] = os.environ[f"{prefix}SNOWFLAKE_SOURCE_TABLE"]
        if sf_source_config:
            result["snowflake_source"] = sf_source_config

        # Snowflake target settings
        sf_target_config: dict[str, Any] = {}
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_ACCOUNT"):
            sf_target_config["account"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_ACCOUNT"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_USERNAME"):
            sf_target_config["username"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_USERNAME"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_PASSWORD"):
            sf_target_config["password"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_PASSWORD"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_ROLE"):
            sf_target_config["role"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_ROLE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_WAREHOUSE"):
            sf_target_config["warehouse"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_WAREHOUSE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_DATABASE"):
            sf_target_config["database"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_DATABASE"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_SCHEMA"):
            sf_target_config["schema"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_SCHEMA"]
        if os.environ.get(f"{prefix}SNOWFLAKE_TARGET_TABLE"):
            sf_target_config["table"] = os.environ[f"{prefix}SNOWFLAKE_TARGET_TABLE"]
        if sf_target_config:
            result["snowflake_target"] = sf_target_config

        # Table settings
        if os.environ.get(f"{prefix}SOURCE_TABLE"):
            result["source_table"] = os.environ[f"{prefix}SOURCE_TABLE"]
        if os.environ.get(f"{prefix}TARGET_TABLE"):
            result["target_table"] = os.environ[f"{prefix}TARGET_TABLE"]

        return result

    def load_from_file(self, file_path: str) -> dict[str, Any]:
        """Load configuration from a file.

        Args:
            file_path: Path to configuration file

        Returns:
            Dictionary of configuration values
        """
        path = pathlib.Path(file_path)
        if not path.exists():
            return {}

        try:
            if path.suffix.lower() in (".yaml", ".yml"):
                with open(path, encoding="utf-8") as f:
                    return yaml.safe_load(f)
            elif path.suffix.lower() == ".json":
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            else:
                msg = f"Unsupported file format: {path.suffix}"
                raise ValueError(msg)
        except Exception as e:
            msg = f"Error loading configuration from {file_path}: {e}"
            raise ValueError(msg) from e

    def load_from_aws_secrets(
        self,
        secret_name: str,
        region: str = "us-east-1",
    ) -> dict[str, Any]:
        """Load configuration from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret
            region: AWS region

        Returns:
            Dictionary of configuration values
        """
        try:
            session = boto3.session.Session()
            client = session.client(service_name="secretsmanager", region_name=region)

            response = client.get_secret_value(SecretId=secret_name)
            secret = response.get("SecretString", "{}")
            return json.loads(secret)
        except (ClientError, NoCredentialsError, json.JSONDecodeError):
            # Log the error but don't fail - secrets are optional
            return {}

    def merge_configs(self, *configs: dict[str, Any]) -> dict[str, Any]:
        """Merge multiple configurations.

        Args:
            *configs: Configuration dictionaries to merge

        Returns:
            Merged configuration dictionary
        """
        result: dict[str, Any] = {}

        for config in configs:
            for key, value in config.items():
                if key not in result:
                    result[key] = value
                elif isinstance(value, dict) and isinstance(result[key], dict):
                    # Recursively merge nested dictionaries
                    result[key] = self.merge_configs(result[key], value)
                else:
                    # Override with the latest value
                    result[key] = value

        return result


@lru_cache
def create_settings(
    env_prefix: str = "",
    config_file: Optional[str] = None,
    aws_secrets_name: Optional[str] = None,
    aws_region: str = "us-east-1",
) -> Settings:
    """Create settings from various sources.

    Args:
        env_prefix: Optional prefix for environment variables
        config_file: Optional path to configuration file
        aws_secrets_name: Optional AWS Secrets Manager secret name
        aws_region: AWS region for AWS services

    Returns:
        Settings object
    """
    loader = ConfigLoader()
    configs = []

    # Load from environment variables
    configs.append(loader.load_from_env(env_prefix))

    # Load from configuration file if provided
    if config_file:
        configs.append(loader.load_from_file(config_file))

    # Load from AWS Secrets Manager if provided
    if aws_secrets_name:
        configs.append(loader.load_from_aws_secrets(aws_secrets_name, aws_region))

    # Merge all configurations
    merged_config = loader.merge_configs(*configs)

    # Create and return settings
    try:
        return Settings(**merged_config)
    except ValidationError as e:
        # Log validation errors and raise
        msg = f"Invalid configuration: {e}"
        raise ValueError(msg) from e


@lru_cache
def get_settings() -> Settings:
    """Get application settings from environment variables.

    Returns:
        Settings object
    """
    config_file = os.environ.get("CONFIG_FILE")
    aws_secrets_name = os.environ.get("AWS_SECRETS_NAME")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    return create_settings(
        config_file=config_file,
        aws_secrets_name=aws_secrets_name,
        aws_region=aws_region,
    )
