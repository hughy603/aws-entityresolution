"""Unified Lambda handlers for AWS Entity Resolution Pipeline.

This module provides unified Lambda function handlers for all steps of the Entity Resolution
pipeline, eliminating code duplication and simplifying deployment.
"""

import time
from typing import Any, Dict

from aws_entity_resolution.config import get_settings
from aws_entity_resolution.extractor.extractor import extract_data
from aws_entity_resolution.loader.loader import load_records
from aws_entity_resolution.processor.processor import (
    find_latest_input_path,
    start_matching_job,
    wait_for_matching_job,
)
from aws_entity_resolution.services import EntityResolutionService, S3Service
from aws_entity_resolution.utils import setup_structured_logging

# Initialize structured logging for Splunk
logger = setup_structured_logging()


def extract_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Extract data from Snowflake to S3.

    Args:
        event: Lambda event data, may include optional overrides for source_table
        context: Lambda context

    Returns:
        Dictionary with extraction results including status and S3 location
    """
    logger.info({"message": "Starting data extraction", "event": event})

    # Get settings
    settings = get_settings()

    # Allow event-based parameter overrides
    if "source_table" in event:
        settings.source_table = event["source_table"]

    # Extract data
    result = extract_data(settings)

    response = {
        "statusCode": 200,
        "body": {
            "status": "success",
            "records_extracted": result.records_extracted,
            "s3_bucket": result.s3_bucket,
            "s3_key": result.s3_key,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    logger.info(
        {
            "message": "Data extraction completed",
            "records_extracted": result.records_extracted,
            "s3_key": result.s3_key,
        }
    )

    return response


def process_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process data through AWS Entity Resolution.

    Args:
        event: Lambda event data, may include s3_key from previous step
        context: Lambda context

    Returns:
        Dictionary with job information including status and job_id
    """
    logger.info({"message": "Starting entity resolution processing", "event": event})

    try:
        # Get settings
        settings = get_settings()

        # Create service instances
        s3_svc = S3Service(settings)
        er_svc = EntityResolutionService(settings)

        # Get input file from previous step or find latest
        input_file = None
        if isinstance(event.get("body"), dict) and "s3_key" in event["body"]:
            input_file = event["body"]["s3_key"]

        # If not provided, find the latest input file
        if not input_file:
            input_file = find_latest_input_path(s3_svc)

        if not input_file:
            raise ValueError("No input data found")

        # Generate timestamp-based output path
        output_prefix = f"{settings.s3.prefix}output/{time.strftime('%Y%m%d_%H%M%S')}/"

        # Start matching job
        job_id = start_matching_job(er_svc, input_file, output_prefix)

        logger.info(
            {
                "message": "Entity resolution job started",
                "job_id": job_id,
                "input_file": input_file,
                "output_prefix": output_prefix,
            }
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
            {
                "message": "Error starting entity resolution job",
                "error": str(e),
            }
        )

        raise


def check_status_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Check the status of an Entity Resolution job.

    Args:
        event: Lambda event with body containing job_id
        context: Lambda context

    Returns:
        Dictionary with job status information
    """
    logger.info({"message": "Checking job status", "event": event})

    try:
        # Get settings
        settings = get_settings()

        # Create service instance
        er_svc = EntityResolutionService(settings)

        # Get job ID from event
        job_id = None
        if isinstance(event.get("body"), dict) and "job_id" in event["body"]:
            job_id = event["body"]["job_id"]

        if not job_id:
            raise ValueError("No job_id provided")

        # Get job status
        status_info = wait_for_matching_job(er_svc, job_id)

        # Determine if job is complete
        is_complete = status_info["status"] in ["COMPLETED", "FAILED", "CANCELED"]

        logger.info(
            {
                "message": "Job status checked",
                "job_id": job_id,
                "status": status_info["status"],
                "is_complete": is_complete,
            }
        )

        return {
            "statusCode": 200,
            "body": {
                "status": status_info["status"].lower(),
                "is_complete": is_complete,
                "job_id": job_id,
                "output_location": status_info.get("output_location", ""),
                "statistics": status_info.get("statistics", {}),
            },
        }
    except Exception as e:
        logger.error(
            {
                "message": "Error checking job status",
                "error": str(e),
            }
        )

        raise


def load_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Load matched records from S3 to Snowflake.

    Args:
        event: Lambda event with output_location from previous step
        context: Lambda context

    Returns:
        Dictionary with loading results
    """
    logger.info({"message": "Starting data loading", "event": event})

    try:
        # Get settings
        settings = get_settings()

        # Get output location from event
        output_location = None
        if isinstance(event.get("body"), dict) and "output_location" in event["body"]:
            output_location = event["body"]["output_location"]

        if not output_location:
            # Find latest output path if not specified
            s3_svc = S3Service(settings)
            output_location = s3_svc.find_latest_path(
                base_prefix=f"{settings.s3.prefix}output/", file_pattern="matches"
            )

        if not output_location:
            raise ValueError("No output data found")

        # Load records
        result = load_records(settings, output_location)

        logger.info(
            {
                "message": "Data loading completed",
                "records_loaded": result.records_loaded,
                "target_table": result.target_table,
            }
        )

        return {
            "statusCode": 200,
            "body": {
                "status": "success",
                "records_loaded": result.records_loaded,
                "target_table": result.target_table,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    except Exception as e:
        logger.error(
            {
                "message": "Error loading data",
                "error": str(e),
            }
        )

        raise


def notify_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Send notification about pipeline execution.

    Args:
        event: Lambda event with notification details
        context: Lambda context

    Returns:
        Dictionary with notification results
    """
    status = event.get("status", "unknown")
    message = event.get("message", "Pipeline execution status update")
    execution_id = event.get("execution", "unknown")
    error = event.get("error")

    logger.info(
        {
            "message": message,
            "status": status,
            "execution_id": execution_id,
            "error": error,
        }
    )

    # Here you would add actual notification logic (SNS, SQS, etc.)
    # For now, just logging the notification

    return {
        "statusCode": 200,
        "body": {
            "message": "Notification sent",
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
