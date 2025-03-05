"""Lambda function to check the status of an AWS Entity Resolution job."""

import json
import logging
from typing import Any

from aws_entity_resolution.config import (
    get_settings,
)
from aws_entity_resolution.services import EntityResolutionService

# Configure logging for Splunk
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - {"message": %(message)s}',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda function handler.

    Args:
        event: Lambda event data containing job_id
        context: Lambda context

    Returns:
        Dictionary containing the job status and results if completed
    """
    try:
        logger.info(
            json.dumps({"message": "Checking entity resolution job status", "event": event})
        )

        # Get required parameters from event
        job_id = event.get("body", {}).get("job_id")
        s3_bucket = event.get("body", {}).get("s3_bucket")

        if not job_id:
            raise ValueError("Missing required parameter: job_id")

        if not s3_bucket:
            # Use default from settings if not provided
            settings = get_settings()
            s3_bucket = settings.s3.bucket

        # Get job status
        er_svc = EntityResolutionService(get_settings())
        job_info = er_svc.get_job_status(job_id)
        status = job_info["status"]

        logger.info(
            json.dumps(
                {
                    "message": "Entity resolution job status",
                    "job_id": job_id,
                    "status": status,
                }
            )
        )

        if status == "SUCCEEDED":
            # Get statistics
            statistics = job_info.get("statistics", {})
            input_records = statistics.get("inputSourceStatistics", {}).get("recordCount", 0)
            matched_records = statistics.get("matchedCount", 0)
            output_location = job_info.get("output_location", "")

            return {
                "statusCode": 200,
                "body": {
                    "status": "completed",
                    "job_id": job_id,
                    "input_records": input_records,
                    "matched_records": matched_records,
                    "s3_bucket": s3_bucket,
                    "s3_key": output_location,
                    "is_complete": True,
                },
            }
        if status in ["FAILED", "STOPPED"]:
            error_message = job_info.get("errors", "Unknown error")
            return {
                "statusCode": 200,
                "body": {
                    "status": "failed",
                    "job_id": job_id,
                    "is_complete": True,
                    "error_message": error_message,
                },
            }
        # Still running
        return {
            "statusCode": 200,
            "body": {
                "status": "running",
                "job_id": job_id,
                "s3_bucket": s3_bucket,
                "is_complete": False,
            },
        }
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "message": "Error checking entity resolution job status",
                    "error": str(e),
                }
            )
        )
        return {
            "statusCode": 500,
            "body": {
                "status": "error",
                "message": str(e),
                "is_complete": True,
            },
        }
