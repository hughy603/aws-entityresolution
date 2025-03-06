"""Tests for Lambda configuration helpers."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Mock the factory import since it doesn't exist
with patch("aws_entity_resolution.config.factory.get_config"):
    from aws_entity_resolution.config.lambda_helpers import (
        configure_lambda_handler,
        get_lambda_env_vars,
    )


def test_get_lambda_env_vars():
    """Test retrieving environment variables for a Lambda function."""
    # Save original environment
    original_env = os.environ.copy()

    try:
        # Set up test environment variables
        test_env = {
            "AWS_REGION": "us-west-2",
            "AWS_ACCESS_KEY_ID": "test-access-key",
            "S3_BUCKET": "test-bucket",
            "ER_SCHEMA_NAME": "test-schema",
            "SNOWFLAKE_ACCOUNT": "test-account",
            "CONFIG_PATH": "config/config.yaml",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "INFO",
            "SOURCE_TABLE": "source_table",
            "TARGET_TABLE": "target_table",
            "PARAMETER_STORE_PATH": "/test/params",
            "IRRELEVANT_VAR": "should-not-be-included",
        }

        # Update environment with test variables
        os.environ.clear()
        os.environ.update(test_env)

        # Call function
        env_vars = get_lambda_env_vars()

        # Check relevant variables are included
        assert "AWS_REGION" in env_vars
        assert "AWS_ACCESS_KEY_ID" in env_vars
        assert "S3_BUCKET" in env_vars
        assert "ER_SCHEMA_NAME" in env_vars
        assert "SNOWFLAKE_ACCOUNT" in env_vars
        assert "CONFIG_PATH" in env_vars
        assert "ENVIRONMENT" in env_vars
        assert "LOG_LEVEL" in env_vars
        assert "SOURCE_TABLE" in env_vars
        assert "TARGET_TABLE" in env_vars
        assert "PARAMETER_STORE_PATH" in env_vars

        # Check irrelevant variables are excluded
        assert "IRRELEVANT_VAR" not in env_vars

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_configure_lambda_handler_success():
    """Test successful configuration of Lambda handler."""

    # Create a mock handler function
    def mock_handler(event, context):
        return {"status": "success", "config": event.get("config")}

    # Apply the decorator
    decorated_handler = configure_lambda_handler(mock_handler)

    # Mock the get_config function
    with patch("aws_entity_resolution.config.lambda_helpers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {"aws": {"region": "us-west-2"}}
        mock_get_config.return_value = mock_config

        # Call the decorated handler
        event = {"param": "value"}
        context = {}
        result = decorated_handler(event, context)

        # Verify the result
        assert result["status"] == "success"
        assert result["config"] == {"aws": {"region": "us-west-2"}}


def test_configure_lambda_handler_error():
    """Test error handling in Lambda handler configuration."""

    # Create a mock handler function
    def mock_handler(event, context):
        return {"status": "success"}

    # Apply the decorator
    decorated_handler = configure_lambda_handler(mock_handler)

    # Mock the get_config function to raise an error
    with patch("aws_entity_resolution.config.lambda_helpers.get_config") as mock_get_config:
        mock_get_config.side_effect = Exception("Configuration error")

        # Call the decorated handler
        event = {"param": "value"}
        context = {}
        result = decorated_handler(event, context)

        # Verify the result
        assert result["status"] == "error"
        assert "error" in result
        assert "Configuration error" in result["error"]


def test_configure_lambda_handler_preserves_event():
    """Test that the Lambda handler decorator preserves original event data."""

    # Create a mock handler function that returns the event
    def mock_handler(event, context):
        return event

    # Apply the decorator
    decorated_handler = configure_lambda_handler(mock_handler)

    # Mock the get_config function
    with patch("aws_entity_resolution.config.lambda_helpers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {"aws": {"region": "us-west-2"}}
        mock_get_config.return_value = mock_config

        # Call the decorated handler with some event data
        original_event = {
            "input_path": "s3://test-bucket/input/",
            "output_path": "s3://test-bucket/output/",
            "parameters": {"param1": "value1", "param2": "value2"},
        }
        context = {}
        result = decorated_handler(original_event, context)

        # Verify the original event data is preserved
        assert result["input_path"] == "s3://test-bucket/input/"
        assert result["output_path"] == "s3://test-bucket/output/"
        assert result["parameters"]["param1"] == "value1"
        assert result["parameters"]["param2"] == "value2"

        # Verify the config was added
        assert "config" in result
        assert result["config"] == {"aws": {"region": "us-west-2"}}


def test_lambda_handler_integration():
    """Test a complete integration of a lambda handler with the decorator."""

    # Define a test handler
    @configure_lambda_handler
    def test_handler(event, context):
        """Test handler that uses configuration."""
        config = event.get("config", {})
        aws_region = config.get("aws", {}).get("region")

        return {
            "status": "success",
            "aws_region": aws_region,
            "input": event.get("input"),
        }

    # Mock the get_config function
    with patch("aws_entity_resolution.config.lambda_helpers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {
            "aws": {"region": "us-west-2"},
            "s3": {"bucket": "test-bucket"},
        }
        mock_get_config.return_value = mock_config

        # Call the handler
        event = {"input": "test-input"}
        context = {}
        result = test_handler(event, context)

        # Verify the result
        assert result["status"] == "success"
        assert result["aws_region"] == "us-west-2"
        assert result["input"] == "test-input"
