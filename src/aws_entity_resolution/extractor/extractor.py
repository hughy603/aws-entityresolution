"""Snowflake to S3 data extraction module."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import boto3
import snowflake.connector
from snowflake.connector import connect

from src.aws_entity_resolution.config import Settings
from src.aws_entity_resolution.services import S3Service, SnowflakeService
from src.aws_entity_resolution.utils import get_logger, handle_exceptions, log_event

logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result of data extraction."""

    success: bool
    output_path: Optional[str] = None
    record_count: int = 0
    error_message: Optional[str] = None
    status: str = "success"
    s3_key: Optional[str] = None


@handle_exceptions("snowflake_connection")
def get_snowflake_connection(settings: Settings) -> snowflake.connector.SnowflakeConnection:
    """Create a connection to Snowflake.

    Args:
        settings: Application settings with Snowflake connection parameters

    Returns:
        Snowflake connection object

    Raises:
        RuntimeError: If connection fails
    """
    try:
        return connect(
            user=settings.snowflake_source.username,
            password=settings.snowflake_source.password,
            account=settings.snowflake_source.account,
            warehouse=settings.snowflake_source.warehouse,
            database=settings.snowflake_source.database,
            schema=settings.snowflake_source.schema,
            role=settings.snowflake_source.role,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Snowflake: {e!s}") from e


@handle_exceptions("snowflake_query")
def execute_query(
    conn: snowflake.connector.SnowflakeConnection, query: str
) -> list[dict[str, Any]]:
    """Execute a query against Snowflake and return results.

    Args:
        conn: Snowflake connection
        query: SQL query to execute

    Returns:
        List of dictionaries representing the query results

    Raises:
        RuntimeError: If query execution fails
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query)

        # Convert results to dictionaries
        column_names = [col[0].lower() for col in cursor.description]
        records = []

        for row in cursor.fetchall():
            record = {column_names[i]: row[i] for i in range(len(column_names))}
            records.append(record)

        return records
    except Exception as e:
        raise RuntimeError(f"Failed to execute Snowflake query: {e!s}") from e
    finally:
        cursor.close()


@handle_exceptions("s3_write")
def write_to_s3(records: list[dict[str, Any]], settings: Settings) -> str:
    """Write records to S3 as NDJSON.

    Args:
        records: List of records to write
        settings: Application settings

    Returns:
        S3 key where data was written

    Raises:
        RuntimeError: If S3 write fails
    """
    try:
        # Generate timestamp for this extraction
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{settings.s3.prefix}{timestamp}/entity_data.json"

        # Format as newline-delimited JSON
        ndjson_data = "\n".join([json.dumps(record) for record in records])

        # Write to S3
        s3_client = boto3.client("s3", region_name=settings.aws_region)
        s3_client.put_object(
            Bucket=settings.s3.bucket, Key=s3_key, Body=ndjson_data, ContentType="application/json"
        )

        return s3_key
    except Exception as e:
        raise RuntimeError(f"Failed to write data to S3: {e!s}") from e


def extract_data(
    settings: Settings,
    dry_run: bool = False,
    snowflake_service: Optional[SnowflakeService] = None,
    s3_service: Optional[S3Service] = None,
) -> ExtractionResult:
    """Extract data from Snowflake to S3.

    Args:
        settings: Application settings
        dry_run: If True, only show what would be extracted without performing the extraction
        snowflake_service: Optional SnowflakeService for dependency injection
        s3_service: Optional S3Service for dependency injection

    Returns:
        ExtractionResult with status and metadata
    """
    # Create or use services
    sf_service = snowflake_service or SnowflakeService(settings)
    s3_svc = s3_service or S3Service(settings)

    try:
        # Prepare query
        attributes = ", ".join(f'"{attr}"' for attr in settings.entity_resolution.entity_attributes)
        query = f'SELECT {attributes} FROM "{settings.source_table}"'

        # If dry run, just return what would happen
        if dry_run:
            logger.info(
                "Dry run mode - would extract from %s.%s.%s to s3://%s/%s",
                settings.snowflake_source.database,
                settings.snowflake_source.schema,
                settings.source_table,
                settings.s3.bucket,
                settings.s3.prefix,
            )
            s3_key = f"{settings.s3.prefix}/dry-run-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            return ExtractionResult(
                success=True,
                output_path=f"s3://{settings.s3.bucket}/{s3_key}",
                status="dry_run",
                s3_key=s3_key,
            )

        # Execute query and get records
        with sf_service:  # Use context manager to handle connection
            records = sf_service.execute_query(query)

        # Generate timestamp for this extraction
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{settings.s3.prefix}{timestamp}/entity_data.json"

        # Format as newline-delimited JSON
        ndjson_data = "\n".join([json.dumps(record) for record in records])

        # Write to S3
        s3_svc.write_object(s3_key, ndjson_data)

        output_path = f"s3://{settings.s3.bucket}/{s3_key}"
        return ExtractionResult(
            success=True,
            output_path=output_path,
            record_count=len(records),
        )
    except Exception as e:
        logger.exception("Error during extraction: %s", str(e))
        return ExtractionResult(
            success=False,
            error_message=str(e),
        )
    finally:
        log_event(logger, "extraction_complete", {"source_table": settings.source_table})
