"""Lambda function to extract data from Snowflake to S3."""

import json
import logging
import os
import time
from typing import Any

from aws_entity_resolution.config import S3Config, Settings, SnowflakeConfig
from aws_entity_resolution.extractor.extractor import extract_data

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
            source_database=os.environ["SNOWFLAKE_SOURCE_DATABASE"],
            source_schema=os.environ["SNOWFLAKE_SOURCE_SCHEMA"],
            source_table=os.environ["SNOWFLAKE_SOURCE_TABLE"],
            target_database="",  # Not needed for extract
            target_schema="",  # Not needed for extract
            target_table="",  # Not needed for extract
        ),
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda function handler.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Dictionary containing the extraction results
    """
    try:
        logger.info(json.dumps({"message": "Starting data extraction", "event": event}))

        # Get settings
        settings = get_settings()

        # Extract data
        result = extract_data(settings)

        logger.info(
            json.dumps(
                {
                    "message": "Data extraction completed",
                    "records_extracted": result.records_extracted,
                    "s3_key": result.s3_key,
                }
            )
        )

        return {
            "statusCode": 200,
            "body": {
                "status": "success",
                "records_extracted": result.records_extracted,
                "s3_bucket": result.s3_bucket,
                "s3_key": result.s3_key,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    except Exception as e:
        logger.error(json.dumps({"message": "Data extraction failed", "error": str(e)}))

        raise
