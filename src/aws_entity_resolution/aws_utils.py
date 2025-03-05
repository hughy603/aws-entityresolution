"""AWS utility functions for the Entity Resolution pipeline."""

from typing import Any, Optional

import boto3

from src.aws_entity_resolution.config import Settings
from src.aws_entity_resolution.utils import get_logger, handle_exceptions, log_event

logger = get_logger(__name__)


@handle_exceptions("s3_list_objects")
def list_s3_objects(
    bucket: str, prefix: str, region: str, delimiter: str = "/"
) -> dict[str, list[str]]:
    """List objects in an S3 bucket with the given prefix.

    Args:
        bucket: S3 bucket name
        prefix: Prefix to filter objects
        region: AWS region
        delimiter: Delimiter for hierarchical listing

    Returns:
        Dictionary with 'prefixes' and 'files' keys containing lists of prefixes and file keys
    """
    s3_client = boto3.client("s3", region_name=region)
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter=delimiter)

    result: dict[str, list[str]] = {"prefixes": [], "files": []}

    # Extract common prefixes (folders)
    if "CommonPrefixes" in response:
        result["prefixes"] = [p["Prefix"] for p in response["CommonPrefixes"]]

    # Extract files
    if "Contents" in response:
        result["files"] = [obj["Key"] for obj in response["Contents"]]

    log_event(
        logger,
        "s3_list_complete",
        {
            "bucket": bucket,
            "prefix": prefix,
            "prefix_count": len(result["prefixes"]),
            "file_count": len(result["files"]),
        },
    )

    return result


@handle_exceptions("s3_find_latest")
def find_latest_s3_path(settings: Settings, file_pattern: str = ".json") -> Optional[str]:
    """Find the latest file in an S3 bucket based on timestamp-prefixed directories.

    Args:
        settings: Application settings
        file_pattern: File extension or pattern to match

    Returns:
        Path to the latest file, or None if not found
    """
    # List timestamp directories
    result = list_s3_objects(settings.s3.bucket, settings.s3.prefix, settings.aws_region)

    if not result["prefixes"]:
        log_event(
            logger,
            "s3_no_directories",
            {"bucket": settings.s3.bucket, "prefix": settings.s3.prefix},
        )
        return None

    # Get the latest directory (assuming timestamp-based naming)
    prefixes = sorted(result["prefixes"], reverse=True)
    latest_prefix = prefixes[0]

    # Find files in the latest directory
    files_result = list_s3_objects(
        settings.s3.bucket,
        latest_prefix,
        settings.aws_region,
        delimiter="",  # No delimiter to get all files
    )

    # Filter for matching files
    matching_files = [f for f in files_result["files"] if file_pattern in f]

    if not matching_files:
        log_event(
            logger,
            "s3_no_matching_files",
            {"bucket": settings.s3.bucket, "prefix": latest_prefix, "pattern": file_pattern},
        )
        return None

    # Get the first matching file
    latest_file = matching_files[0]

    log_event(logger, "s3_latest_file_found", {"bucket": settings.s3.bucket, "key": latest_file})

    return latest_file


@handle_exceptions("entity_resolution_job")
def start_entity_resolution_job(settings: Settings, input_file: str, output_prefix: str) -> str:
    """Start an AWS Entity Resolution matching job.

    Args:
        settings: Application settings
        input_file: S3 path to the input file
        output_prefix: S3 prefix for the output

    Returns:
        Job ID of the started matching job
    """
    client = boto3.client("entityresolution", region_name=settings.aws_region)

    log_event(
        logger,
        "matching_job_start",
        {
            "workflow": settings.entity_resolution.workflow_name,
            "input_file": input_file,
            "output_prefix": output_prefix,
        },
    )

    response = client.start_matching_job(
        workflowName=settings.entity_resolution.workflow_name,
        inputSourceConfig={"s3SourceConfig": {"bucket": settings.s3.bucket, "key": input_file}},
        outputSourceConfig={
            "s3OutputConfig": {
                "bucket": settings.s3.bucket,
                "key": output_prefix,
                "applyNormalization": True,
            }
        },
    )

    job_id = response["jobId"]

    log_event(
        logger,
        "matching_job_started",
        {"job_id": job_id, "workflow": settings.entity_resolution.workflow_name},
    )

    return job_id


@handle_exceptions("entity_resolution_job_status")
def get_entity_resolution_job_status(settings: Settings, job_id: str) -> dict[str, Any]:
    """Get the status of an AWS Entity Resolution matching job.

    Args:
        settings: Application settings
        job_id: Job ID to check

    Returns:
        Dictionary with job status information
    """
    client = boto3.client("entityresolution", region_name=settings.aws_region)

    response = client.get_matching_job(jobId=job_id)
    status = response["jobStatus"]

    log_event(logger, "matching_job_status", {"job_id": job_id, "status": status})

    return {
        "status": status,
        "output_location": response.get("outputSourceConfig", {})
        .get("s3OutputConfig", {})
        .get("key", ""),
        "statistics": response.get("statistics", {}),
        "errors": response.get("errors", []),
    }
