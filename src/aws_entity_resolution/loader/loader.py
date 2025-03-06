"""Module for loading matched records from S3 to Snowflake."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aws_entity_resolution.config import Settings
from aws_entity_resolution.services.s3 import S3Service
from aws_entity_resolution.services.snowflake import SnowflakeService
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger, log_event

logger = get_logger(__name__)


@dataclass
class LoadingResult:
    """Result of loading matched records to Snowflake."""

    status: str
    records_loaded: int
    target_table: str
    error_message: str | None = None
    execution_time: float | None = None

    def __init__(
        self: "LoadingResult",
        status: str,
        records_loaded: int,
        target_table: str,
        error_message: str | None = None,
        execution_time: float | None = None,
        **kwargs: dict[str, Any],  # Accept additional keyword arguments
    ) -> None:
        """Initialize with required fields, ignoring additional kwargs for test compatibility."""
        self.status = status
        self.records_loaded = records_loaded
        self.target_table = target_table
        self.error_message = error_message
        self.execution_time = execution_time


@handle_exceptions("get_table_schema")
def get_table_schema(settings: Settings) -> list[str]:
    """Get table schema definition from AWS Entity Resolution service.

    Instead of hardcoding the schema, this function fetches it from AWS.

    Args:
        settings: Application settings containing AWS config

    Returns:
        List of column definitions for table creation
    """
    # Standard columns that are always included
    columns = [
        "ID VARCHAR NOT NULL",
        "MATCH_ID VARCHAR",
        "MATCH_SCORE FLOAT",
        "LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()",
        "PRIMARY KEY (ID)",
    ]

    # Fetch schema information from AWS Entity Resolution
    # This replaces the hardcoded columns
    try:
        import boto3

        client = boto3.client("entityresolution", region_name=settings.aws.region)
        response = client.get_schema(
            schemaName=settings.entity_resolution.schema_name,
        )

        # Add columns from AWS Entity Resolution schema
        for attribute in response.get("attributes", []):
            name = attribute.get("name")
            attr_type = attribute.get("type")

            # Map AWS Entity Resolution types to Snowflake types
            if (
                attr_type == "STRING"
                or attr_type == "EMAIL"
                or attr_type == "PHONE"
                or attr_type == "ID"
            ):
                sf_type = "VARCHAR"
            elif attr_type == "NUMBER":
                sf_type = "FLOAT"
            elif attr_type == "DATE":
                sf_type = "TIMESTAMP_NTZ"
            else:
                sf_type = "VARCHAR"  # Default type

            # Skip ID as it's already included
            if name.upper() != "ID":
                columns.append(f"{name.upper()} {sf_type}")

    except Exception as e:
        logger.warning(f"Failed to fetch schema from AWS Entity Resolution: {e}")
        # Fallback to basic columns if AWS schema fetch fails
        logger.info("Using fallback schema definition for Snowflake table")

    return columns


@handle_exceptions("create_target_table")
def create_target_table(
    snowflake_service: SnowflakeService, table_name: str, settings: Settings
) -> None:
    """Create the target table for entity resolution results.

    Args:
        snowflake_service: Snowflake service instance
        table_name: Name of the table to create
        settings: Application settings

    Raises:
        RuntimeError: If Snowflake connection is not established
    """
    if not snowflake_service.connection:
        msg = "Snowflake connection is not established"
        raise RuntimeError(msg)

    # Get columns from AWS Entity Resolution schema
    columns = get_table_schema(settings)

    # Create the table
    snowflake_service.create_table(table_name, columns)
    logger.info("Created target table: %s", table_name)


@handle_exceptions("setup_snowflake_objects")
def setup_snowflake_objects(snowflake_service: SnowflakeService, settings: Settings) -> None:
    """Set up required Snowflake objects for loading data.

    Args:
        snowflake_service: Snowflake service instance
        settings: Application settings
    """
    if not snowflake_service.connection:
        msg = "Snowflake connection is not established"
        raise RuntimeError(msg)

    # Read SQL setup script
    setup_sql_path = Path(__file__).parent / "snowflake_setup.sql"
    with open(setup_sql_path) as f:
        setup_sql = f.read()

    # Parameters for SQL
    params = {
        "bucket": settings.s3.bucket,
        "prefix": settings.s3.prefix,
        "storage_integration_name": getattr(
            settings.snowflake_target, "storage_integration", "default_integration"
        ),
        "target_table": settings.target_table,
        "target_table_stream": f"{settings.target_table}_stream",
    }

    # Execute setup statements - replace references with proper bind variables
    cursor = snowflake_service.connection.cursor()
    for statement in setup_sql.split(";"):
        if statement.strip():
            cursor.execute(statement, params)

    snowflake_service.connection.commit()

    # Create or update the target table
    create_target_table(snowflake_service, settings.target_table, settings)


@handle_exceptions("load_matched_records")
def load_matched_records(
    s3_key: str,
    snowflake_service: SnowflakeService,
    settings: Settings,
) -> int:
    """Load matched records from S3 to Snowflake using MERGE.

    Args:
        s3_key: S3 key containing the matched records
        snowflake_service: Snowflake service instance
        settings: Application settings

    Returns:
        Number of records loaded
    """
    if not snowflake_service.connection:
        msg = "Snowflake connection is not established"
        raise RuntimeError(msg)

    cursor = snowflake_service.connection.cursor()

    # Create temporary table
    temp_table = f"{settings.target_table}_temp"
    create_temp_sql = "CREATE TEMPORARY TABLE IF NOT EXISTS :temp_table LIKE :target_table"
    cursor.execute(
        create_temp_sql,
        {"temp_table": temp_table, "target_table": settings.target_table},
    )

    # Copy data from S3 to temporary table
    copy_sql = """
    COPY INTO :temp_table
    FROM @entity_resolution_stage/:s3_key
    FILE_FORMAT = entity_resolution_json_format
    ON_ERROR = 'ABORT_STATEMENT';
    """
    cursor.execute(copy_sql, {"temp_table": temp_table, "s3_key": s3_key})

    # Prepare dynamic MERGE statement based on existing columns
    desc_sql = "DESC TABLE :table_name"
    cursor.execute(desc_sql, {"table_name": settings.target_table})
    columns = [row[0] for row in cursor.fetchall() if row[0] not in ("LAST_UPDATED")]

    # Build dynamic MERGE SQL statement
    set_clause = ", ".join([f"{col} = source.{col}" for col in columns if col != "ID"])
    insert_cols = ", ".join([*columns, "LAST_UPDATED"])
    values_clause = ", ".join([f"source.{col}" for col in columns] + ["CURRENT_TIMESTAMP()"])

    merge_sql = f"""
    MERGE INTO {settings.target_table} target
    USING {temp_table} source
    ON target.ID = source.ID
    WHEN MATCHED THEN
        UPDATE SET {set_clause}, LAST_UPDATED = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT ({insert_cols})
        VALUES ({values_clause});
    """

    result = cursor.execute(merge_sql)
    snowflake_service.connection.commit()

    # Get number of affected rows
    stats = result.fetchone()
    return stats[0] if stats else 0


def load_records(
    settings: Settings,
    s3_key: str | None = None,
    dry_run: bool = False,
    s3_service: S3Service | None = None,
    snowflake_service: SnowflakeService | None = None,
) -> LoadingResult:
    """Load matched records from S3 to Snowflake.

    Args:
        settings: Application settings
        s3_key: S3 key to load data from (if None, will find latest)
        dry_run: If True, simulate the loading without actually writing to Snowflake
        s3_service: Optional S3Service for dependency injection
        snowflake_service: Optional SnowflakeService for dependency injection

    Returns:
        LoadingResult with status and metadata
    """
    # Create or use service instances
    s3_svc = s3_service or S3Service(settings)
    sf_svc = snowflake_service or SnowflakeService(settings, use_target=True)

    start_time = time.time()

    # Dry run mode - return early without loading data
    if dry_run:
        logger.info("Performing dry run - no data will be loaded")
        return LoadingResult(
            status="dry_run",
            records_loaded=0,
            target_table=settings.target_table,
            execution_time=time.time() - start_time,
        )

    try:
        # Find the latest output file if no key is provided
        if not s3_key:
            output_prefix = f"{settings.s3.prefix}{settings.s3.output_prefix}"
            s3_key = s3_svc.find_latest_path(output_prefix, "results")

            if not s3_key:
                return LoadingResult(
                    status="error",
                    records_loaded=0,
                    target_table=settings.target_table,
                    error_message="No matched records found in S3",
                )

        # Set up Snowflake objects
        setup_snowflake_objects(sf_svc, settings)

        # Load the records
        log_event("loading_matched_records", s3_key=s3_key)
        records_loaded = load_matched_records(s3_key, sf_svc, settings)

        return LoadingResult(
            status="success",
            records_loaded=records_loaded,
            target_table=settings.target_table,
            execution_time=time.time() - start_time,
        )

    except Exception as e:
        error_message = str(e)
        logger.exception("Error loading records: %s", error_message)
        return LoadingResult(
            status="error",
            records_loaded=0,
            target_table=settings.target_table,
            error_message=error_message,
            execution_time=time.time() - start_time,
        )
