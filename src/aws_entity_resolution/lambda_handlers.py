"""Unified Lambda handlers for AWS Entity Resolution Pipeline.

This module provides unified Lambda function handlers for all steps of the Entity Resolution
pipeline, eliminating code duplication and simplifying deployment.
"""

import logging
import os
from typing import Any

import boto3

from aws_entity_resolution.config.lambda_helpers import configure_lambda_handler
from aws_entity_resolution.config.unified import get_settings as get_config
from aws_entity_resolution.services.entity_resolution import EntityResolutionService
from aws_entity_resolution.services.snowflake import SnowflakeService
from aws_entity_resolution.utils.logging import setup_structured_logging

# Initialize structured logging for Splunk
logger = logging.getLogger(__name__)
setup_structured_logging()

# Set default log level
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(log_level)


@configure_lambda_handler
def create_glue_table_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Create an AWS Glue table pointing to S3 data.

    Args:
        event: Lambda event containing database, table_name, s3_path, and schema
        context: Lambda context

    Returns:
        Lambda response with table creation status
    """
    logger.info("Creating AWS Glue table")

    # Get configuration
    config = get_config()

    # Extract parameters
    database = event.get("database")
    if not database:
        msg = "Missing required parameter: database"
        raise ValueError(msg)

    table_name = event.get("table_name")
    if not table_name:
        msg = "Missing required parameter: table_name"
        raise ValueError(msg)

    s3_path = event.get("s3_path")
    if not s3_path:
        msg = "Missing required parameter: s3_path"
        raise ValueError(msg)

    # Schema is required to define the table structure
    schema = event.get("schema", [])
    if not schema:
        msg = "Missing required parameter: schema"
        raise ValueError(msg)

    # Source format (CSV, JSON, Parquet, etc.)
    format_type = event.get("format", "csv")

    # Initialize Glue client
    glue_client = boto3.client("glue", region_name=config.aws_region)

    # Extract S3 bucket and prefix from S3 path
    s3_parts = s3_path.replace("s3://", "").split("/", 1)
    s3_parts[0]
    s3_parts[1] if len(s3_parts) > 1 else ""

    # Create or update the table
    try:
        # Check if table exists
        try:
            glue_client.get_table(DatabaseName=database, Name=table_name)
            table_exists = True
        except glue_client.exceptions.EntityNotFoundException:
            table_exists = False

        # Define table input structure
        table_input = {
            "Name": table_name,
            "StorageDescriptor": {
                "Columns": schema,
                "Location": s3_path,
                "InputFormat": get_input_format(format_type),
                "OutputFormat": get_output_format(format_type),
                "SerdeInfo": get_serde_info(format_type),
                "Parameters": {
                    "classification": format_type,
                },
            },
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {
                "EXTERNAL": "TRUE",
            },
        }

        # Create or update the table
        if table_exists:
            glue_client.update_table(
                DatabaseName=database,
                TableInput=table_input,
            )
            action = "updated"
        else:
            glue_client.create_table(
                DatabaseName=database,
                TableInput=table_input,
            )
            action = "created"

        logger.info(
            f"Successfully {action} Glue table {database}.{table_name} pointing to {s3_path}",
        )

        return {
            "status": "completed",
            "action": action,
            "database": database,
            "table_name": table_name,
            "s3_path": s3_path,
        }

    except glue_client.exceptions.AccessDeniedException as e:
        logger.exception(f"Access denied when creating Glue table: {e!s}")
        raise
    except glue_client.exceptions.AlreadyExistsException as e:
        logger.exception(f"Glue table already exists: {e!s}")
        raise
    except glue_client.exceptions.ResourceNumberLimitExceededException as e:
        logger.exception(f"Resource limit exceeded when creating Glue table: {e!s}")
        raise
    except glue_client.exceptions.InvalidInputException as e:
        logger.exception(f"Invalid input when creating Glue table: {e!s}")
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.exception(f"Error in input parameters when creating Glue table: {e!s}")
        raise
    except Exception as e:
        logger.critical(f"Unexpected error when creating Glue table: {e!s}")
        raise


def get_input_format(format_type: str) -> str:
    """Get the appropriate input format based on the file format.

    Args:
        format_type: The file format (csv, json, parquet, etc.)

    Returns:
        The Hadoop input format class
    """
    formats = {
        "csv": "org.apache.hadoop.mapred.TextInputFormat",
        "json": "org.apache.hadoop.mapred.TextInputFormat",
        "parquet": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
        "avro": "org.apache.hadoop.hive.ql.io.avro.AvroContainerInputFormat",
        "orc": "org.apache.hadoop.hive.ql.io.orc.OrcInputFormat",
    }
    return formats.get(format_type.lower(), "org.apache.hadoop.mapred.TextInputFormat")


def get_output_format(format_type: str) -> str:
    """Get the appropriate output format based on the file format.

    Args:
        format_type: The file format (csv, json, parquet, etc.)

    Returns:
        The Hadoop output format class
    """
    formats = {
        "csv": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
        "json": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
        "parquet": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
        "avro": "org.apache.hadoop.hive.ql.io.avro.AvroContainerOutputFormat",
        "orc": "org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat",
    }
    return formats.get(
        format_type.lower(),
        "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
    )


def get_serde_info(format_type: str) -> dict[str, Any]:
    """Get the appropriate SerDe information based on the file format.

    Args:
        format_type: The file format (csv, json, parquet, etc.)

    Returns:
        The SerDe information as a dictionary
    """
    serde_info = {
        "csv": {
            "SerializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
            "Parameters": {
                "separatorChar": ",",
                "quoteChar": '"',
                "escapeChar": "\\",
            },
        },
        "json": {
            "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
            "Parameters": {},
        },
        "parquet": {
            "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
            "Parameters": {},
        },
        "avro": {
            "SerializationLibrary": "org.apache.hadoop.hive.serde2.avro.AvroSerDe",
            "Parameters": {},
        },
        "orc": {
            "SerializationLibrary": "org.apache.hadoop.hive.ql.io.orc.OrcSerde",
            "Parameters": {},
        },
    }
    return serde_info.get(
        format_type.lower(),
        {
            "SerializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
            "Parameters": {
                "separatorChar": ",",
                "quoteChar": '"',
                "escapeChar": "\\",
            },
        },
    )


@configure_lambda_handler
def entity_resolution_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Start an AWS Entity Resolution job.

    Args:
        event: Lambda event containing input_table, workflow_name, and output_path
        context: Lambda context

    Returns:
        Lambda response with job ID
    """
    logger.info("Starting Entity Resolution job")

    # Get configuration
    config = get_config()

    # Extract parameters
    input_table = event.get("input_table")
    if not input_table:
        msg = "Missing required parameter: input_table"
        raise ValueError(msg)

    workflow_name = event.get("workflow_name", config.entity_resolution.workflow_name)
    output_path = event.get("output_path", f"s3://{config.s3.bucket}/{config.s3.output_prefix}")
    database = event.get("database", "")

    # Initialize Entity Resolution service
    er_service = EntityResolutionService(config)

    # Start the job
    job_id = er_service.start_matching_job(
        input_source=f"arn:aws:glue:{config.aws_region}::table/{database}/{input_table}",
        workflow_name=workflow_name,
        output_path=output_path,
    )

    response = {
        "status": "started",
        "job_id": job_id,
        "workflow_name": workflow_name,
        "output_path": output_path,
    }

    logger.info(f"Entity Resolution job started with ID: {job_id}")
    return response


def get_account_id() -> str:
    """Get the current AWS account ID.

    Returns:
        The AWS account ID
    """
    sts_client = boto3.client("sts")
    return sts_client.get_caller_identity()["Account"]


@configure_lambda_handler
def check_entity_resolution_job_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Check the status of an AWS Entity Resolution job.

    Args:
        event: Lambda event containing job_id
        context: Lambda context

    Returns:
        Lambda response with job status
    """
    logger.info("Checking Entity Resolution job status")

    # Get configuration
    config = get_config()

    # Extract parameters
    job_id = event.get("job_id")
    if not job_id:
        msg = "Missing required parameter: job_id"
        raise ValueError(msg)

    # Initialize Entity Resolution service
    er_service = EntityResolutionService(config)

    # Check job status
    status = er_service.get_matching_job_status(job_id)

    response = {
        "status": "in_progress" if status == "IN_PROGRESS" else "completed",
        "job_status": status,
        "job_id": job_id,
    }

    if status == "SUCCEEDED":
        # Get job output location
        output_path = event.get("output_path")
        if output_path:
            response["output_path"] = output_path

    logger.info(f"Entity Resolution job {job_id} status: {status}")
    return response


@configure_lambda_handler
def snowflake_load_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Load data from S3 to Snowflake.

    Args:
        event: Lambda event containing s3_path and target_table
        context: Lambda context

    Returns:
        Lambda response with load status
    """
    logger.info("Starting Snowflake load process")

    # Get configuration
    config = get_config()

    # Extract parameters
    s3_path = event.get("s3_path")
    if not s3_path:
        msg = "Missing required parameter: s3_path"
        raise ValueError(msg)

    target_table = event.get("target_table", config.snowflake_target.table)
    file_format = event.get("file_format", "CSV")

    # Initialize Snowflake service
    snowflake_service = SnowflakeService(config)

    # Load data to Snowflake
    rows_loaded = snowflake_service.load_data_from_s3(
        s3_path=s3_path,
        target_table=target_table,
        file_format=file_format,
    )

    response = {
        "status": "completed",
        "rows_loaded": rows_loaded,
        "target_table": target_table,
        "s3_path": s3_path,
    }

    logger.info(f"Snowflake load completed: {rows_loaded} rows loaded to {target_table}")
    return response


@configure_lambda_handler
def notify_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Send notification about the Entity Resolution process.

    Args:
        event: Lambda event containing status and details
        context: Lambda context

    Returns:
        Lambda response with notification status
    """
    logger.info("Processing notification")

    # Get configuration
    _config = get_config()

    # Extract parameters
    status = event.get("status", "completed")
    details = event.get("details", {})

    # Log the notification
    logger.info(f"Entity Resolution process {status}: {details}")

    # In a real implementation, this would send an email, SNS notification, etc.
    # For now, we just log the notification

    return {
        "status": "completed",
        "notification_sent": True,
        "process_status": status,
        "details": details,
    }
