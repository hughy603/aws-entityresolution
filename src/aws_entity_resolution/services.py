"""Service classes for AWS Entity Resolution using dependency injection pattern."""

from typing import Any, Optional

import boto3
import snowflake.connector
from snowflake.connector import SnowflakeConnection, connect

from src.aws_entity_resolution.config import Settings
from src.aws_entity_resolution.utils import get_logger, handle_exceptions, log_event

logger = get_logger(__name__)


class S3Service:
    """S3 service for interacting with AWS S3."""

    def __init__(self, settings: Settings) -> None:
        """Initialize with settings."""
        self.settings = settings
        self.client = boto3.client("s3", region_name=settings.aws_region)

    @handle_exceptions("s3_list_objects")
    def list_objects(self, prefix: str, delimiter: str = "/") -> dict[str, list[str]]:
        """List objects in the S3 bucket with the given prefix.

        Returns:
            Dictionary with 'prefixes' and 'files' keys containing lists of prefixes and file keys
        """
        response = self.client.list_objects_v2(
            Bucket=self.settings.s3.bucket, Prefix=prefix, Delimiter=delimiter
        )

        result = {"prefixes": [], "files": []}

        # Extract prefixes (folders)
        if "CommonPrefixes" in response:
            result["prefixes"] = [p["Prefix"] for p in response["CommonPrefixes"]]

        # Extract files
        if "Contents" in response:
            result["files"] = [obj["Key"] for obj in response["Contents"]]

        log_event(
            logger,
            "s3_list_complete",
            {
                "bucket": self.settings.s3.bucket,
                "prefix": prefix,
                "prefix_count": len(result["prefixes"]),
                "file_count": len(result["files"]),
            },
        )

        return result

    @handle_exceptions("s3_write")
    def write_object(self, key: str, data: str) -> None:
        """Write data to an S3 object."""
        self.client.put_object(Body=data, Bucket=self.settings.s3.bucket, Key=key)

        log_event(
            logger,
            "s3_write_success",
            {"bucket": self.settings.s3.bucket, "key": key, "size": len(data)},
        )

    @handle_exceptions("s3_read")
    def read_object(self, key: str) -> str:
        """Read data from an S3 object."""
        response = self.client.get_object(Bucket=self.settings.s3.bucket, Key=key)

        data = response["Body"].read().decode("utf-8")

        log_event(
            logger,
            "s3_read_success",
            {"bucket": self.settings.s3.bucket, "key": key, "size": len(data)},
        )

        return data

    @handle_exceptions("s3_find_latest")
    def find_latest_path(self, base_prefix: str = "", file_pattern: str = ".json") -> Optional[str]:
        """Find the latest file in the S3 bucket based on timestamp-prefixed directories.

        Args:
            base_prefix: Base prefix to look under (defaults to settings.s3.prefix)
            file_pattern: File extension or pattern to match

        Returns:
            Path to the latest file, or None if not found
        """
        prefix = base_prefix or self.settings.s3.prefix

        # List timestamp directories
        result = self.list_objects(prefix)

        if not result["prefixes"]:
            log_event(
                logger, "s3_no_directories", {"bucket": self.settings.s3.bucket, "prefix": prefix}
            )
            return None

        # Get the latest directory (assuming timestamp-based naming)
        prefixes = sorted(result["prefixes"], reverse=True)
        latest_prefix = prefixes[0]

        # Find files in the latest directory
        files_result = self.list_objects(latest_prefix, delimiter="")

        # Filter for matching files
        matching_files = [f for f in files_result["files"] if file_pattern in f]

        if not matching_files:
            log_event(
                logger,
                "s3_no_matching_files",
                {
                    "bucket": self.settings.s3.bucket,
                    "prefix": latest_prefix,
                    "pattern": file_pattern,
                },
            )
            return None

        # Get the first matching file
        latest_file = matching_files[0]

        log_event(
            logger, "s3_latest_file_found", {"bucket": self.settings.s3.bucket, "key": latest_file}
        )

        return latest_file


class EntityResolutionService:
    """Service for interacting with AWS Entity Resolution."""

    def __init__(self, settings: Settings) -> None:
        """Initialize with settings."""
        self.settings = settings
        self.client = boto3.client("entityresolution", region_name=settings.aws_region)

    @handle_exceptions("entity_resolution_job")
    def start_matching_job(self, input_file: str, output_prefix: str) -> str:
        """Start an AWS Entity Resolution matching job.

        Args:
            input_file: S3 path to the input file
            output_prefix: S3 prefix for the output

        Returns:
            Job ID of the started matching job
        """
        log_event(
            logger,
            "matching_job_start",
            {
                "workflow": self.settings.entity_resolution.workflow_name,
                "input_file": input_file,
                "output_prefix": output_prefix,
            },
        )

        response = self.client.start_matching_job(
            workflowName=self.settings.entity_resolution.workflow_name,
            inputSourceConfig={
                "s3SourceConfig": {"bucket": self.settings.s3.bucket, "key": input_file}
            },
            outputSourceConfig={
                "s3OutputConfig": {
                    "bucket": self.settings.s3.bucket,
                    "key": output_prefix,
                    "applyNormalization": True,
                }
            },
        )

        job_id = response["jobId"]

        log_event(
            logger,
            "matching_job_started",
            {"job_id": job_id, "workflow": self.settings.entity_resolution.workflow_name},
        )

        return job_id

    @handle_exceptions("entity_resolution_job_status")
    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of an AWS Entity Resolution matching job.

        Args:
            job_id: Job ID to check

        Returns:
            Dictionary with job status information
        """
        response = self.client.get_matching_job(jobId=job_id)
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


class SnowflakeService:
    """Service for interacting with Snowflake."""

    def __init__(self, settings: Settings, use_target: bool = False) -> None:
        """Initialize with settings.

        Args:
            settings: Application settings
            use_target: Whether to use target connection details (True) or source (False)
        """
        self.settings = settings
        self.use_target = use_target
        self.connection = None
        self.cursor = None

    @property
    def config(self):
        """Get the appropriate Snowflake configuration (source or target)."""
        return self.settings.snowflake_target if self.use_target else self.settings.snowflake_source

    @handle_exceptions("snowflake_connection")
    def connect(self) -> SnowflakeConnection:
        """Create and return a Snowflake connection."""
        if self.connection and not self.connection.is_closed():
            return self.connection

        self.connection = connect(
            user=self.config.username,
            password=self.config.password,
            account=self.config.account,
            warehouse=self.config.warehouse,
            database=self.config.database,
            schema=self.config.schema,
            role=self.config.role,
        )

        log_event(
            logger,
            "snowflake_connection_success",
            {
                "database": self.config.database,
                "schema": self.config.schema,
                "warehouse": self.config.warehouse,
                "type": "target" if self.use_target else "source",
            },
        )

        return self.connection

    def disconnect(self) -> None:
        """Close the Snowflake connection if open."""
        if self.cursor:
            try:
                self.cursor.close()
            except (AttributeError, snowflake.connector.errors.Error) as e:
                log_event(logger, "cursor_close_error", {"error": str(e)})
            self.cursor = None

        if self.connection and not self.connection.is_closed():
            self.connection.close()
            self.connection = None
            log_event(
                logger,
                "snowflake_connection_closed",
                {"type": "target" if self.use_target else "source"},
            )

    @handle_exceptions("snowflake_query")
    def execute_query(self, query: str) -> list[dict[str, str]]:
        """Execute a Snowflake query and return results as a list of dictionaries.

        Creates a connection if one doesn't exist.
        """
        conn = self.connect()
        cursor = conn.cursor()
        self.cursor = cursor  # Store for potential cleanup later

        try:
            log_event(logger, "snowflake_query_start", {"query": query})

            cursor.execute(query)
            results = cursor.fetchall()
            column_names = [col[0].lower() for col in cursor.description]

            # Convert results to list of dictionaries
            records = []
            for row in results:
                record = {}
                for i, value in enumerate(row):
                    record[column_names[i]] = value
                records.append(record)

            log_event(
                logger, "snowflake_query_complete", {"query": query, "row_count": len(records)}
            )

            return records
        finally:
            if cursor:
                cursor.close()
                if self.cursor == cursor:
                    self.cursor = None

    def __enter__(self) -> "SnowflakeService":
        """Context manager enter method."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit method."""
        self.disconnect()
