"""Lambda function to process data through AWS Entity Resolution."""

import json
import logging
from typing import Any

from aws_entity_resolution.config import (
    get_settings,
)
from aws_entity_resolution.processor.processor import (
    find_latest_input_path,
    start_matching_job,
)
from aws_entity_resolution.services import EntityResolutionService, S3Service

# Configure logging for Splunk
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - {"message": %(message)s}',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda function handler.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Dictionary containing the job information
    """
    try:
        logger.info(
            json.dumps({"message": "Starting entity resolution processing", "event": event})
        )

        # Get settings from environment variables
        settings = get_settings()

        # Create service instances
        s3_svc = S3Service(settings)
        er_svc = EntityResolutionService(settings)

        # Find latest input file
        input_file = find_latest_input_path(s3_svc)
        if not input_file:
            raise ValueError("No input data found")

        # Generate timestamp-based output path
        import time

        output_prefix = f"{settings.s3.prefix}output/{time.strftime('%Y%m%d_%H%M%S')}/"

        # Start matching job but don't wait for completion
        job_id = start_matching_job(er_svc, input_file, output_prefix)

        logger.info(
            json.dumps(
                {
                    "message": "Entity resolution job started",
                    "job_id": job_id,
                    "input_file": input_file,
                    "output_prefix": output_prefix,
                }
            )
        )

        return {
            "statusCode": 200,
            "body": {
                "status": "running",
                "job_id": job_id,
                "s3_bucket": settings.s3.bucket,
                "input_file": input_file,
                "output_prefix": output_prefix,
            },
        }
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "message": "Error starting entity resolution job",
                    "error": str(e),
                }
            )
        )
        return {
            "statusCode": 500,
            "body": {
                "status": "error",
                "message": str(e),
            },
        }
