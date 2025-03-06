"""Tests for the unified configuration module."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from botocore.exceptions import ClientError

from aws_entity_resolution.config.unified import (
    ConfigLoader,
    Environment,
    LogLevel,
    Settings,
    create_settings,
)


class TestConfigLoader:
    """Tests for the ConfigLoader class."""

    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.setenv("ENTITY_RESOLUTION_WORKFLOW_ID", "test-workflow")
        monkeypatch.setenv("SNOWFLAKE_TARGET_ACCOUNT", "test-account")
        monkeypatch.setenv("TARGET_TABLE", "TEST_TABLE")

        # Load configuration
        loader = ConfigLoader()
        config = loader.load_from_env()

        # Check configuration
        assert config["environment"] == "test"
        assert config["log_level"] == "DEBUG"
        assert config["aws"]["region"] == "us-west-2"
        assert config["s3"]["bucket"] == "test-bucket"
        assert config["entity_resolution"]["workflow_id"] == "test-workflow"
        assert config["snowflake_target"]["account"] == "test-account"
        assert config["target_table"] == "TEST_TABLE"

    def test_load_from_file_yaml(self) -> None:
        """Test loading configuration from a YAML file."""
        # Create a temporary YAML file
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(
                {
                    "environment": "test",
                    "log_level": "DEBUG",
                    "aws": {"region": "us-west-2"},
                    "s3": {"bucket": "test-bucket"},
                    "entity_resolution": {"workflow_id": "test-workflow"},
                    "snowflake_target": {"account": "test-account"},
                    "target_table": "TEST_TABLE",
                },
                f,
            )

        try:
            # Load configuration
            loader = ConfigLoader()
            config = loader.load_from_file(f.name)

            # Check configuration
            assert config["environment"] == "test"
            assert config["log_level"] == "DEBUG"
            assert config["aws"]["region"] == "us-west-2"
            assert config["s3"]["bucket"] == "test-bucket"
            assert config["entity_resolution"]["workflow_id"] == "test-workflow"
            assert config["snowflake_target"]["account"] == "test-account"
            assert config["target_table"] == "TEST_TABLE"
        finally:
            # Clean up
            os.unlink(f.name)

    def test_merge_configs(self) -> None:
        """Test merging configurations."""
        # Create configurations
        config1: dict[str, Any] = {
            "environment": "dev",
            "aws": {"region": "us-east-1"},
            "s3": {"bucket": "dev-bucket"},
        }
        config2: dict[str, Any] = {
            "environment": "test",
            "aws": {"profile": "test"},
            "snowflake_target": {"account": "test-account"},
        }

        # Merge configurations
        loader = ConfigLoader()
        merged = loader.merge_configs(config1, config2)

        # Check merged configuration
        assert merged["environment"] == "test"  # Overridden
        assert merged["aws"]["region"] == "us-east-1"  # Preserved
        assert merged["aws"]["profile"] == "test"  # Added
        assert merged["s3"]["bucket"] == "dev-bucket"  # Preserved
        assert merged["snowflake_target"]["account"] == "test-account"  # Added


class TestSettings:
    """Tests for the Settings class."""

    def test_create_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating settings."""
        # Set environment variables
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.setenv("ENTITY_RESOLUTION_WORKFLOW_ID", "test-workflow")
        monkeypatch.setenv("SNOWFLAKE_TARGET_ACCOUNT", "test-account")
        monkeypatch.setenv("TARGET_TABLE", "TEST_TABLE")

        # Create settings
        settings = create_settings()

        # Check settings
        assert settings.environment == Environment.TEST
        assert settings.log_level == LogLevel.DEBUG
        assert settings.aws.region == "us-west-2"
        assert settings.s3.bucket == "test-bucket"
        assert settings.entity_resolution.workflow_id == "test-workflow"
        assert settings.snowflake_target.account == "test-account"
        assert settings.target_table == "TEST_TABLE"

    def test_set_aws_region_defaults(self) -> None:
        """Test setting AWS region defaults."""
        # Create settings
        settings = Settings(
            aws={"region": "us-west-2"},
        )

        # Check settings
        assert settings.aws.region == "us-west-2"
        assert settings.s3.region == "us-west-2"  # Should inherit from aws.region
