"""AWS Entity Resolution processing module."""

import time
from dataclasses import dataclass
from typing import Any, Optional, Union

from aws_entity_resolution.config import Settings
from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.s3 import S3Service
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger, log_event

logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result of entity resolution processing."""

    status: str
    job_id: str
    input_records: int
    matched_records: int
    s3_bucket: str
    s3_key: str
    success: bool = False
    output_path: str = ""
    error_message: str = ""

    def __init__(
        self: "ProcessingResult",
        status: str,
        job_id: str,
        input_records: int,
        matched_records: int,
        s3_bucket: str,
        s3_key: str,
        success: bool = False,
        output_path: str = "",
        error_message: str = "",
        **kwargs: dict[str, Any],  # Accept additional keyword arguments
    ) -> None:
        """Initialize with required fields, ignoring additional kwargs for test compatibility."""
        self.status = status
        self.job_id = job_id
        self.input_records = input_records
        self.matched_records = matched_records
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.success = status == "success"
        self.output_path = f"s3://{s3_bucket}/{s3_key}" if s3_bucket and s3_key else ""
        self.error_message = error_message


@handle_exceptions("find_latest_input_path")
def find_latest_input_path(s3_service: S3Service) -> Optional[str]:
    """Find the latest input file path in S3.

    Args:
        s3_service: S3Service instance

    Returns:
        The S3 path to the latest input file or None if not found
    """
    return s3_service.find_latest_path()


@handle_exceptions("start_matching_job")
def start_matching_job(
    er_service: EntityResolutionService,
    input_path: str,
    output_prefix: str,
) -> str:
    """Start an Entity Resolution matching job.

    Args:
        er_service: EntityResolutionService instance
        input_path: S3 path to the input file
        output_prefix: S3 prefix for the output

    Returns:
        Job ID of the started matching job
    """
    return er_service.start_matching_job(input_path, output_prefix)


@handle_exceptions("processing_job_wait")
def wait_for_matching_job(
    er_service_or_settings: Union[EntityResolutionService, Settings],
    job_id: str,
    check_interval: int = 30,
) -> dict[str, Any]:
    """Wait for a matching job to complete.

    Args:
        er_service_or_settings: Entity resolution service or settings
        job_id: Job ID to check
        check_interval: Seconds between status checks

    Returns:
        Dictionary with job information and statistics
    """
    # Create EntityResolutionService if Settings was passed
    if isinstance(er_service_or_settings, Settings):
        er_service = EntityResolutionService(er_service_or_settings)
    else:
        er_service = er_service_or_settings

    while True:
        job_info = er_service.get_job_status(job_id)
        status = job_info["status"]

        if status == "SUCCEEDED":
            # Get output location from job info
            output_location = job_info.get("output_location")

            # If output_location is not in job_info, try to extract it from outputSourceConfig
            if not output_location and "outputSourceConfig" in job_info:
                output_config = job_info.get("outputSourceConfig", {})
                s3_config = output_config.get("s3OutputConfig", {})
                output_location = s3_config.get("key", "")

            log_event(
                "matching_job_success",
                job_id=job_id,
                output_location=output_location,
                statistics=job_info.get("statistics", {}),
            )

            # Add output_location to job_info if it's not there
            if "output_location" not in job_info and output_location:
                job_info["output_location"] = output_location

            return job_info
        if status == "FAILED":
            error_message = job_info.get("errors", ["Unknown error"])[0]
            log_event(
                "matching_job_failed",
                job_id=job_id,
                error=error_message,
            )
            msg = f"Matching job failed: {error_message}"
            raise RuntimeError(msg)
        if status == "CANCELLED":
            log_event(
                "matching_job_cancelled",
                job_id=job_id,
            )
            msg = "Matching job was cancelled"
            raise RuntimeError(msg)
        # Job still running, wait and check again
        time.sleep(check_interval)


def process_data(
    settings: Settings,
    s3_service: Optional[S3Service] = None,
    er_service: Optional[EntityResolutionService] = None,
    dry_run: bool = False,
    wait: bool = True,
    input_uri: Optional[str] = None,
    output_file: Optional[str] = None,
    matching_threshold: Optional[float] = None,
) -> ProcessingResult:
    """Process entity data through AWS Entity Resolution.

    Args:
        settings: Application settings
        s3_service: Optional S3Service for dependency injection
        er_service: Optional EntityResolutionService for dependency injection
        dry_run: If True, only simulate processing without making actual changes
        wait: If True, wait for processing to complete
        input_uri: Optional URI of input data (s3://bucket/key)
        output_file: Optional custom output filename
        matching_threshold: Optional matching confidence threshold

    Returns:
        ProcessingResult with processing status and stats
    """
    # Set up services if not provided
    s3_service = s3_service or S3Service(settings)
    er_service = er_service or EntityResolutionService(settings)

    # If dry run, just return a dummy result
    if dry_run:
        return ProcessingResult(
            status="dry_run",
            job_id="dry-run-job-id",
            input_records=0,
            matched_records=0,
            s3_bucket=settings.s3.bucket,
            s3_key=f"{settings.s3.prefix}/dry-run-output/",
            success=True,
            output_path=f"s3://{settings.s3.bucket}/{settings.s3.prefix}/dry-run-output/",
        )

    try:
        # Find latest input file or use provided input URI
        input_file = input_uri if input_uri else find_latest_input_path(s3_service)
        if not input_file:
            msg = "No input data found"
            raise ValueError(msg)

        # Generate timestamp-based output path or use provided output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_prefix = f"{settings.s3.prefix}output/{output_file or timestamp}/"

        # Start matching job
        job_id = start_matching_job(er_service, input_file, output_prefix)

        if not wait:
            # If not waiting, return a result with the job ID but no statistics
            return ProcessingResult(
                status="submitted",
                job_id=job_id,
                input_records=0,
                matched_records=0,
                s3_bucket=settings.s3.bucket,
                s3_key=output_prefix,
                success=True,
                output_path=f"s3://{settings.s3.bucket}/{output_prefix}",
            )

        # Wait for job completion
        result = wait_for_matching_job(er_service, job_id)

        # Get statistics
        input_records = result["statistics"].get("inputRecordCount", 0)
        matched_records = result["statistics"].get("matchedRecordCount", 0)

        return ProcessingResult(
            status="success",
            job_id=job_id,
            input_records=input_records,
            matched_records=matched_records,
            s3_bucket=settings.s3.bucket,
            s3_key=result["output_location"],
            success=True,
            output_path=f"s3://{settings.s3.bucket}/{result['output_location']}",
        )
    finally:
        log_event("processing_complete")
