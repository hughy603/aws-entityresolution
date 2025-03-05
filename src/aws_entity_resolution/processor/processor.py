"""AWS Entity Resolution processing module."""

import time
from dataclasses import dataclass
from typing import Any, Optional, Union

from src.aws_entity_resolution.config import Settings
from src.aws_entity_resolution.services import EntityResolutionService, S3Service
from src.aws_entity_resolution.utils import get_logger, handle_exceptions, log_event

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
        self,
        status: str,
        job_id: str,
        input_records: int,
        matched_records: int,
        s3_bucket: str,
        s3_key: str,
        success: bool = False,
        output_path: str = "",
        error_message: str = "",
        **kwargs,  # Accept additional keyword arguments
    ):
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
    er_service: EntityResolutionService, input_path: str, output_prefix: str
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
            log_event(
                logger,
                "matching_job_success",
                {
                    "job_id": job_id,
                    "output_location": job_info["output_location"],
                    "statistics": job_info["statistics"],
                },
            )
            return job_info
        elif status in ["FAILED", "CANCELLED"]:
            error_message = job_info.get("errors") or "Unknown error"
            raise RuntimeError(f"Matching job failed: {error_message}")

        time.sleep(check_interval)


def process_data(
    settings: Settings,
    s3_service: Optional[S3Service] = None,
    er_service: Optional[EntityResolutionService] = None,
    dry_run: bool = False,
) -> ProcessingResult:
    """Process entity data through AWS Entity Resolution.

    Args:
        settings: Application settings
        s3_service: Optional S3Service for dependency injection
        er_service: Optional EntityResolutionService for dependency injection
        dry_run: If True, only simulate processing without making actual changes

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
        # Find latest input file
        input_file = find_latest_input_path(s3_service)
        if not input_file:
            raise ValueError("No input data found")

        # Generate timestamp-based output path
        output_prefix = f"{settings.s3.prefix}output/{time.strftime('%Y%m%d_%H%M%S')}/"

        # Start matching job
        job_id = start_matching_job(er_service, input_file, output_prefix)

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
        log_event(logger, "processing_complete", {})
