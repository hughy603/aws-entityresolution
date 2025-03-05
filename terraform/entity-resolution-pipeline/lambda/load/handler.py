"""Lambda function to load matched records from S3 to Snowflake."""

import json
import logging
import os
from typing import Any

from aws_entity_resolution.config import (
    EntityResolutionConfig,
    S3Config,
    Settings,
    SnowflakeConfig,
)
from aws_entity_resolution.loader.loader import load_records

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_settings() -> Settings:
    """Get settings from environment variables."""
    return Settings(
        aws_region=os.environ["AWS_REGION"],
        s3=S3Config(bucket=os.environ["S3_BUCKET_NAME"], prefix=os.environ["S3_PREFIX"]),
        snowflake=SnowflakeConfig(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            username=os.environ["SNOWFLAKE_USERNAME"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            role=os.environ["SNOWFLAKE_ROLE"],
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
            source_database="",  # Not needed for load
            source_schema="",  # Not needed for load
            source_table="",  # Not needed for load
            target_database=os.environ["SNOWFLAKE_TARGET_DATABASE"],
            target_schema=os.environ["SNOWFLAKE_TARGET_SCHEMA"],
            target_table=os.environ["SNOWFLAKE_TARGET_TABLE"],
        ),
        entity_resolution=EntityResolutionConfig(
            workflow_name="",  # Not needed for load
            schema_name="",  # Not needed for load
            entity_attributes=os.environ["ER_ENTITY_ATTRIBUTES"].split(","),
        ),
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda function handler.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Dictionary containing the loading results
    """
    try:
        logger.info(json.dumps({"message": "Starting data loading", "event": event}))

        # Get matched data location from previous step
        input_data = event.get("body", {})
        if not input_data or "s3_key" not in input_data:
            raise ValueError("No input data location provided from previous step")

        # Get settings
        settings = get_settings()

        # Load records
        result = load_records(settings, input_data["s3_key"])

        logger.info(
            json.dumps(
                {
                    "message": "Data loading completed",
                    "records_loaded": result.records_loaded,
                    "target_table": result.target_table,
                }
            )
        )

        return {
            "statusCode": 200,
            "body": {
                "status": result.status,
                "records_loaded": result.records_loaded,
                "target_table": result.target_table,
                "error_message": result.error_message,
            },
        }

    except Exception as e:
        logger.error(json.dumps({"message": "Data loading failed", "error": str(e)}))

        raise
