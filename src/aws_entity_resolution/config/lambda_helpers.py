"""Lambda configuration helpers for Entity Resolution pipeline.

This module provides helper functions for configuring Lambda functions
with environment variables and S3 configuration.
"""

import os
from collections.abc import Callable
from typing import Any

from aws_entity_resolution.config.factory import ConfigurationError, get_config


def get_lambda_env_vars() -> dict[str, str]:
    """Get all environment variables for a Lambda function.

    Returns:
        Dictionary of environment variables present in the Lambda environment
    """
    # Only return environment variables relevant to configuration
    relevant_prefixes = [
        "AWS_",
        "S3_",
        "ER_",
        "SNOWFLAKE_",
        "CONFIG_",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "SOURCE_TABLE",
        "TARGET_TABLE",
        "PARAMETER_STORE_PATH",
    ]

    env_vars = {}
    for key, value in os.environ.items():
        if any(key.startswith(prefix) for prefix in relevant_prefixes):
            env_vars[key] = value

    return env_vars


def configure_lambda_handler(
    handler_func: Callable[[dict[str, Any], Any], dict[str, Any]],
) -> Callable[[dict[str, Any], Any], dict[str, Any]]:
    """Decorator to configure Lambda handlers with configuration.

    This decorator adds the application configuration to the Lambda event
    for use by the handler function.

    Args:
        handler_func: Lambda handler function to decorate

    Returns:
        Decorated handler function
    """

    def wrapper(event: dict[str, Any], context: Any) -> dict[str, Any]:
        try:
            # Get configuration
            config = get_config()

            # Add configuration to event
            if isinstance(event, dict) and "config" not in event:
                event["config"] = {
                    "environment": config.environment.value,
                    "aws_region": config.aws.region,
                    "s3_bucket": config.s3.bucket,
                    "s3_prefix": config.s3.prefix,
                    "er_workflow_name": config.entity_resolution.workflow_name,
                    "er_schema_name": config.entity_resolution.schema_name,
                }

            # Call handler with configuration
            return handler_func(event, context)
        except ConfigurationError as e:
            # Log the error and raise
            print(f"Configuration error: {e!s}")
            raise

    return wrapper


# Example Lambda handler using the decorator
@configure_lambda_handler
def example_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Example Lambda handler that uses configuration.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Lambda response
    """
    # Get configuration
    config = get_config()

    # Use configuration in handler logic
    s3_bucket = config.s3.bucket
    s3_prefix = config.s3.prefix
    workflow_name = config.entity_resolution.workflow_name

    # Process data using configuration
    return {
        "status": "success",
        "message": f"Processed data using workflow {workflow_name}",
        "config": {
            "s3_bucket": s3_bucket,
            "s3_prefix": s3_prefix,
            "workflow_name": workflow_name,
        },
    }
