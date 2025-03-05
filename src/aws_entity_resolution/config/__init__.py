"""Configuration management for AWS Entity Resolution pipeline."""

import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file if present
load_dotenv()


class SnowflakeConfig(BaseModel):
    """Snowflake connection configuration."""

    account: str = Field("", description="Snowflake account identifier")
    username: str = Field("", description="Snowflake username")
    password: str = Field("", description="Snowflake password")
    role: str = Field(default="ACCOUNTADMIN", description="Snowflake role to use")
    warehouse: str = Field("", description="Snowflake warehouse to use")
    database: str = Field("", description="Snowflake database name")
    schema: str = Field("", description="Snowflake schema name")

    model_config = ConfigDict(protected_namespaces=())


class S3Config(BaseModel):
    """S3 configuration."""

    bucket: str = Field("", description="S3 bucket name")
    prefix: str = Field("", description="S3 prefix for data")
    region: str = Field(default="us-east-1", description="AWS region for S3")


class EntityResolutionConfig(BaseModel):
    """Entity Resolution configuration."""

    workflow_name: str = Field("", description="Entity Resolution workflow name")
    schema_name: str = Field("", description="Entity Resolution schema name")
    entity_attributes: list[str] = Field(
        default=["id", "name", "email", "phone", "address", "company"],
        description="List of entity attributes",
    )

    @field_validator("entity_attributes", mode="before")
    @classmethod
    def parse_entity_attributes(cls, value: Any) -> list[str]:
        """Parse entity attributes from string if needed."""
        if isinstance(value, str):
            return [attr.strip() for attr in value.split(",")]
        if isinstance(value, list):
            return [str(attr) for attr in value]
        return []


def create_snowflake_config() -> SnowflakeConfig:
    """Create a new SnowflakeConfig instance."""
    return SnowflakeConfig(
        account="",
        username="",
        password="",
        role="ACCOUNTADMIN",
        warehouse="",
        database="",
        schema="",
    )


def create_s3_config() -> S3Config:
    """Create a new S3Config instance."""
    return S3Config(bucket="", prefix="", region="us-east-1")


def create_entity_resolution_config() -> EntityResolutionConfig:
    """Create a new EntityResolutionConfig instance."""
    return EntityResolutionConfig(
        workflow_name="",
        schema_name="",
        entity_attributes=["id", "name", "email", "phone", "address", "company"],
    )


class Settings(BaseSettings):
    """Global settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")

    # Snowflake Source Configuration
    snowflake_source: SnowflakeConfig = Field(default_factory=create_snowflake_config)

    # Snowflake Target Configuration
    snowflake_target: SnowflakeConfig = Field(default_factory=create_snowflake_config)

    # S3 Configuration
    s3: S3Config = Field(default_factory=create_s3_config)

    # Entity Resolution Configuration
    entity_resolution: EntityResolutionConfig = Field(
        default_factory=create_entity_resolution_config
    )

    # Table Configuration
    source_table: str = Field(default="", alias="SOURCE_TABLE")
    target_table: str = Field(default="GOLDEN_ENTITY_RECORDS", alias="TARGET_TABLE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("aws_region", mode="before")
    @classmethod
    def validate_aws_region(cls, value: str) -> str:
        """Validate AWS region, allowing override from AWS_DEFAULT_REGION."""
        # For tests, we need to respect the explicitly provided value
        if value != "us-east-1" or not os.environ.get("AWS_DEFAULT_REGION"):
            return value
        return os.environ.get("AWS_DEFAULT_REGION", value)


def get_settings() -> Settings:
    """Get application settings."""
    settings = Settings()

    # Apply sensible defaults for snowflake source
    if not settings.snowflake_source.account:
        account_env = os.getenv("SNOWFLAKE_ACCOUNT", "")
        settings.snowflake_source.account = account_env
    if not settings.snowflake_source.username:
        username_env = os.getenv("SNOWFLAKE_USERNAME", "")
        settings.snowflake_source.username = username_env
    if not settings.snowflake_source.password:
        password_env = os.getenv("SNOWFLAKE_PASSWORD", "")
        settings.snowflake_source.password = password_env
    if not settings.snowflake_source.warehouse:
        warehouse_env = os.getenv("SNOWFLAKE_WAREHOUSE", "")
        settings.snowflake_source.warehouse = warehouse_env
    if not settings.snowflake_source.database:
        db_env = os.getenv("SNOWFLAKE_SOURCE_DATABASE", "")
        settings.snowflake_source.database = db_env
    if not settings.snowflake_source.schema:
        schema_env = os.getenv("SNOWFLAKE_SOURCE_SCHEMA", "")
        settings.snowflake_source.schema = schema_env

    # Apply sensible defaults for snowflake target
    if not settings.snowflake_target.account and os.getenv("SNOWFLAKE_ACCOUNT"):
        account_env = os.getenv("SNOWFLAKE_ACCOUNT", "")
        settings.snowflake_target.account = account_env
    if not settings.snowflake_target.username and os.getenv("SNOWFLAKE_USERNAME"):
        username_env = os.getenv("SNOWFLAKE_USERNAME", "")
        settings.snowflake_target.username = username_env
    if not settings.snowflake_target.password and os.getenv("SNOWFLAKE_PASSWORD"):
        password_env = os.getenv("SNOWFLAKE_PASSWORD", "")
        settings.snowflake_target.password = password_env
    if not settings.snowflake_target.warehouse and os.getenv("SNOWFLAKE_WAREHOUSE"):
        warehouse_env = os.getenv("SNOWFLAKE_WAREHOUSE", "")
        settings.snowflake_target.warehouse = warehouse_env
    if not settings.snowflake_target.database:
        db_env = os.getenv("SNOWFLAKE_TARGET_DATABASE", "")
        settings.snowflake_target.database = db_env
    if not settings.snowflake_target.schema:
        schema_env = os.getenv("SNOWFLAKE_TARGET_SCHEMA", "")
        settings.snowflake_target.schema = schema_env

    # Apply sensible defaults for S3
    if not settings.s3.bucket:
        bucket_env = os.getenv("S3_BUCKET_NAME", "")
        settings.s3.bucket = bucket_env
    if not settings.s3.prefix:
        prefix_env = os.getenv("S3_PREFIX", "")
        settings.s3.prefix = prefix_env
    if settings.s3.region == "us-east-1" and settings.aws_region != "us-east-1":
        settings.s3.region = settings.aws_region

    # Entity resolution config
    if not settings.entity_resolution.workflow_name:
        workflow_env = os.getenv("ER_WORKFLOW_NAME", "")
        settings.entity_resolution.workflow_name = workflow_env
    if not settings.entity_resolution.schema_name:
        schema_env = os.getenv("ER_SCHEMA_NAME", "")
        settings.entity_resolution.schema_name = schema_env
    if os.getenv("ER_ENTITY_ATTRIBUTES") and len(settings.entity_resolution.entity_attributes) == 6:
        settings.entity_resolution.entity_attributes = (
            settings.entity_resolution.parse_entity_attributes(
                os.getenv("ER_ENTITY_ATTRIBUTES", "")
            )
        )

    return settings
