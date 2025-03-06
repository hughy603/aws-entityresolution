"""Lambda handler for Snowflake data loading operations.

This module contains Lambda handlers that interact with Snowflake
for loading Entity Resolution output data.
"""

import json
import logging
from typing import Any

from aws_entity_resolution.config.settings import get_settings
from aws_entity_resolution.loader.loader import load_records
from aws_entity_resolution.services.s3 import S3Service
from aws_entity_resolution.services.snowflake import SnowflakeService
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import configure_logging, log_event

# Configure logging
logger = logging.getLogger(__name__)
configure_logging()


@handle_exceptions("load_to_snowflake")
def load_to_snowflake(s3_key: str, dry_run: bool = False) -> dict[str, Any]:
    """Load Entity Resolution output data from S3 to Snowflake.

    Args:
        s3_key: S3 key containing the matched records
        dry_run: If True, only simulate the loading operation

    Returns:
        Dictionary with loading results

    Raises:
        Exception: If loading operation fails
    """
    settings = get_settings()

    # Initialize services
    s3_service = S3Service(settings)
    snowflake_service = SnowflakeService(settings, use_target=True)

    # Load the records
    result = load_records(
        settings=settings,
        s3_key=s3_key,
        dry_run=dry_run,
        s3_service=s3_service,
        snowflake_service=snowflake_service,
    )

    # Format the result
    return {
        "status": result.status,
        "records_loaded": result.records_loaded,
        "target_table": result.target_table,
        "error_message": result.error_message,
        "execution_time": result.execution_time,
    }


@handle_exceptions("find_latest_results")
def find_latest_results() -> str:
    """Find the latest Entity Resolution results in S3.

    Returns:
        S3 key of the latest results file

    Raises:
        Exception: If no results are found
    """
    settings = get_settings()
    s3_service = S3Service(settings)

    output_prefix = f"{settings.s3.prefix}{settings.s3.output_prefix}"
    latest_key = s3_service.find_latest_path(output_prefix, "results")

    if not latest_key:
        msg = f"No results found in {output_prefix}"
        raise FileNotFoundError(msg)

    return latest_key


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for Snowflake data loading operations.

    This handler manages loading Entity Resolution output data to Snowflake.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Response data for API Gateway or Step Functions
    """
    operation = event.get("operation", "LOAD_DATA")

    # Log event with structured data
    log_event("snowflake_lambda_invoked", operation=operation)

    if operation == "LOAD_DATA":
        s3_key = event.get("s3_key")
        dry_run = event.get("dry_run", False)

        if not s3_key:
            try:
                # If no key provided, find the latest results
                s3_key = find_latest_results()
                logger.info(f"Using latest results file: {s3_key}")
            except Exception as e:
                return {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "error": f"No S3 key provided and no latest results found: {e!s}",
                        }
                    ),
                }

        try:
            result = load_to_snowflake(s3_key, dry_run)
            return {
                "statusCode": 200,
                "body": json.dumps(result),
            }
        except Exception as e:
            logger.exception(f"Error loading data to Snowflake: {e!s}")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    elif operation == "FIND_LATEST_RESULTS":
        try:
            latest_key = find_latest_results()
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "s3_key": latest_key,
                    }
                ),
            }
        except Exception as e:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": f"Unsupported operation: {operation}",
                }
            ),
        }
