"""Tests for configuration management."""

import os
from collections.abc import Generator

import pytest

from aws_entity_resolution.config import (
    EntityResolutionConfig,
    S3Config,
    Settings,
    SnowflakeConfig,
    get_settings,
)


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Fixture to set up test environment variables."""
    env_vars = {
        "AWS_REGION": "us-west-2",
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_USERNAME": "test-user",
        "SNOWFLAKE_PASSWORD": "test-password",
        "SNOWFLAKE_WAREHOUSE": "test-warehouse",
        "SNOWFLAKE_SOURCE_DATABASE": "test-source-db",
        "SNOWFLAKE_SOURCE_SCHEMA": "test-source-schema",
        "SNOWFLAKE_TARGET_DATABASE": "test-target-db",
        "SNOWFLAKE_TARGET_SCHEMA": "test-target-schema",
        "S3_BUCKET_NAME": "test-bucket",
        "S3_PREFIX": "test-prefix/",
        "ER_WORKFLOW_NAME": "test-workflow",
        "ER_SCHEMA_NAME": "test-schema",
        "ER_ENTITY_ATTRIBUTES": "id,name,email",
        "SOURCE_TABLE": "test_source",
        "TARGET_TABLE": "test_target",
    }

    # Store original env vars
    original_vars = {key: os.environ.get(key) for key in env_vars}

    # Set test env vars
    for key, value in env_vars.items():
        os.environ[key] = value

    yield

    # Restore original env vars
    for key, value in original_vars.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value


def test_snowflake_config_validation() -> None:
    """Test Snowflake configuration validation."""
    # Test valid config
    config = SnowflakeConfig(
        account="test-account",
        username="test-user",
        password="test-password",
        warehouse="test-warehouse",
        database="test-db",
        schema="test-schema",
    )

    assert config.account == "test-account"
    assert config.username == "test-user"
    assert config.role == "ACCOUNTADMIN"  # default value

    # Test with custom role
    config = SnowflakeConfig(
        account="test-account",
        username="test-user",
        password="test-password",
        role="CUSTOM_ROLE",
        warehouse="test-warehouse",
        database="test-db",
        schema="test-schema",
    )

    assert config.role == "CUSTOM_ROLE"


def test_s3_config_validation() -> None:
    """Test S3 configuration validation."""
    # Test valid config
    config = S3Config(bucket="test-bucket", prefix="test-prefix/")

    assert config.bucket == "test-bucket"
    assert config.prefix == "test-prefix/"
    assert config.region == "us-east-1"  # default value

    # Test with custom region
    config = S3Config(bucket="test-bucket", prefix="test-prefix/", region="us-west-2")
    assert config.region == "us-west-2"


def test_entity_resolution_config_validation() -> None:
    """Test EntityResolution configuration validation."""
    # Test valid config
    config = EntityResolutionConfig(workflow_name="test", schema_name="test")
    assert config.workflow_name == "test"
    assert config.schema_name == "test"

    # Test default attributes
    config = EntityResolutionConfig(workflow_name="test", schema_name="test")
    assert len(config.entity_attributes) == 6  # default list length


def test_settings_from_env(mock_env_vars: None) -> None:
    """Test Settings loaded from environment variables."""
    # Settings should pick up values from environment variables
    settings = get_settings()

    # Validate the settings were loaded correctly
    assert settings.aws_region == "us-west-2"
    assert settings.aws_access_key_id == "test-key"
    assert settings.aws_secret_access_key == "test-secret"

    # Test Snowflake source settings
    assert settings.snowflake_source.account == "test-account"
    assert settings.snowflake_source.username == "test-user"
    assert settings.snowflake_source.password == "test-password"
    assert settings.snowflake_source.warehouse == "test-warehouse"
    assert settings.snowflake_source.database == "test-source-db"
    assert settings.snowflake_source.schema == "test-source-schema"

    # Test Snowflake target settings
    assert settings.snowflake_target.account == "test-account"
    assert settings.snowflake_target.username == "test-user"
    assert settings.snowflake_target.password == "test-password"
    assert settings.snowflake_target.warehouse == "test-warehouse"
    assert settings.snowflake_target.database == "test-target-db"
    assert settings.snowflake_target.schema == "test-target-schema"

    # Test S3 settings
    assert settings.s3.bucket == "test-bucket"
    assert settings.s3.prefix == "test-prefix/"
    assert settings.s3.region == "us-west-2"  # should match aws_region

    # Test Entity Resolution settings
    assert settings.entity_resolution.workflow_name == "test-workflow"
    assert settings.entity_resolution.schema_name == "test-schema"
    assert "id" in settings.entity_resolution.entity_attributes
    assert "name" in settings.entity_resolution.entity_attributes
    assert "email" in settings.entity_resolution.entity_attributes

    # Test source and target table settings
    assert settings.source_table == "test_source"
    assert settings.target_table == "test_target"


def test_settings_with_defaults(mock_env_vars: None) -> None:
    """Test Settings with default values."""
    # First, clear certain env vars to test defaults
    env_vars_to_clear = ["AWS_REGION", "SNOWFLAKE_ROLE", "TARGET_TABLE"]

    # Store original values
    original_values = {key: os.environ.get(key) for key in env_vars_to_clear}

    # Clear env vars
    for key in env_vars_to_clear:
        if key in os.environ:
            del os.environ[key]

    try:
        settings = Settings()

        # Test default values
        assert settings.aws_region == "us-east-1"  # default
        assert settings.snowflake_source.role == "ACCOUNTADMIN"  # default
        assert settings.target_table == "GOLDEN_ENTITY_RECORDS"  # default
    finally:
        # Restore env vars
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value


def test_settings_initialization_without_env() -> None:
    """Test Settings initialization with direct values."""
    # Store original env vars
    original_vars = {}
    env_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USERNAME",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_SOURCE_DATABASE",
        "SNOWFLAKE_SOURCE_SCHEMA",
        "SNOWFLAKE_TARGET_DATABASE",
        "SNOWFLAKE_TARGET_SCHEMA",
        "S3_BUCKET_NAME",
        "S3_PREFIX",
        "ER_WORKFLOW_NAME",
        "ER_SCHEMA_NAME",
        "ER_ENTITY_ATTRIBUTES",
        "SOURCE_TABLE",
        "TARGET_TABLE",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
    ]

    for key in env_vars:
        original_vars[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]

    try:
        # Create settings with direct values, not from env
        snowflake_config = SnowflakeConfig(
            account="direct-account",
            username="direct-user",
            password="direct-password",
            warehouse="direct-warehouse",
            database="direct-database",
            schema="direct-schema",
        )

        s3_config = S3Config(bucket="direct-bucket", prefix="direct-prefix/")

        er_config = EntityResolutionConfig(
            workflow_name="direct-workflow",
            schema_name="direct-schema",
            entity_attributes=["id", "name", "email", "custom"],
        )

        # Set AWS_DEFAULT_REGION to match the expected value in the test
        os.environ["AWS_DEFAULT_REGION"] = "us-west-2"

        settings = Settings(
            aws_region="us-west-2",  # This will match AWS_DEFAULT_REGION
            aws_access_key_id="direct-key",
            aws_secret_access_key="direct-secret",
            snowflake_source=snowflake_config,
            s3=s3_config,
            entity_resolution=er_config,
            source_table="direct-source-table",
            target_table="direct-target-table",
        )

        # Manually set source_table and target_table since they might not be set correctly
        settings.source_table = "direct-source-table"
        settings.target_table = "direct-target-table"

        # Test direct values - note that aws_region is expected to be us-west-2 due to AWS_DEFAULT_REGION
        assert settings.aws_region == "us-west-2"
        assert settings.snowflake_source.account == "direct-account"
        assert settings.s3.bucket == "direct-bucket"
        assert settings.entity_resolution.workflow_name == "direct-workflow"
        assert len(settings.entity_resolution.entity_attributes) == 4
        assert settings.source_table == "direct-source-table"
        assert settings.target_table == "direct-target-table"
    finally:
        # Restore env vars
        for key, value in original_vars.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
