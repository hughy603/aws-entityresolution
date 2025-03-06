"""Snowflake data loading module.

This module provides functions for loading Entity Resolution output data into Snowflake.
"""

import logging
import time
from typing import Any

import snowflake.connector

from aws_entity_resolution.config.settings import get_settings
from aws_entity_resolution.services.entity_resolution import get_schema

logger = logging.getLogger(__name__)


def get_snowflake_connection(use_target=True):
    """Get a Snowflake connection.

    Args:
        use_target: If True, use target connection settings; otherwise, use source

    Returns:
        Snowflake connection object
    """
    settings = get_settings()

    # Choose the appropriate Snowflake config
    sf_config = settings.snowflake_target if use_target else settings.snowflake_source

    # Create connection
    return snowflake.connector.connect(
        account=sf_config.account,
        user=sf_config.username,
        password=sf_config.password.get_secret_value(),
        role=sf_config.role,
        warehouse=sf_config.warehouse,
        database=sf_config.database,
        schema=sf_config.schema,
    )


def get_table_columns_from_schema(schema_name: str) -> list[str]:
    """Get table column definitions from Entity Resolution schema.

    Args:
        schema_name: Name of the Entity Resolution schema

    Returns:
        List of Snowflake column definitions
    """
    # Standard columns that are always included
    columns = [
        "ID VARCHAR NOT NULL",
        "MATCH_ID VARCHAR",
        "MATCH_SCORE FLOAT",
        "LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()",
        "PRIMARY KEY (ID)",
    ]

    # Get schema from AWS
    schema_info = get_schema(schema_name)

    # Add columns from schema
    for attr in schema_info.get("attributes", []):
        name = attr.get("name")
        attr_type = attr.get("type")

        # Skip ID as it's already included
        if name and name.upper() != "ID":
            # Map Entity Resolution types to Snowflake types
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
                sf_type = "VARCHAR"

            columns.append(f"{name.upper()} {sf_type}")

    return columns


def create_table(connection, table_name: str, schema_name: str) -> bool:
    """Create a Snowflake table based on Entity Resolution schema.

    Args:
        connection: Snowflake connection
        table_name: Name of the table to create
        schema_name: Name of the Entity Resolution schema

    Returns:
        True if successful, False otherwise
    """
    # Get column definitions from schema
    columns = get_table_columns_from_schema(schema_name)

    # Create SQL statement
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {", ".join(columns)}
    )
    """

    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        connection.commit()
        logger.info(f"Created table {table_name}")
        return True
    except Exception as e:
        logger.exception(f"Failed to create table: {e}")
        return False
    finally:
        cursor.close()


def load_data(
    s3_path: str,
    target_table: str,
    schema_name: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Load data from S3 to Snowflake.

    Args:
        s3_path: S3 path to load data from
        target_table: Target Snowflake table
        schema_name: Name of the Entity Resolution schema
        dry_run: If True, don't actually load data

    Returns:
        Result information
    """
    start_time = time.time()
    settings = get_settings()

    if dry_run:
        logger.info(f"DRY RUN: Would load data from {s3_path} to {target_table}")
        return {
            "status": "success",
            "records_loaded": 0,
            "target_table": target_table,
            "dry_run": True,
            "execution_time": time.time() - start_time,
        }

    try:
        # Connect to Snowflake
        conn = get_snowflake_connection(use_target=True)

        # Create the table if it doesn't exist
        create_table(conn, target_table, schema_name)

        # Create a temporary table for loading
        temp_table = f"{target_table}_temp"
        cursor = conn.cursor()

        # Create temp table with same structure
        cursor.execute(f"CREATE TEMPORARY TABLE IF NOT EXISTS {temp_table} LIKE {target_table}")

        # Load data from S3
        cursor.execute(f"""
        COPY INTO {temp_table}
        FROM '{s3_path}'
        FILE_FORMAT = (TYPE = 'JSON')
        """)

        # Get column list for dynamic merge
        cursor.execute(f"DESC TABLE {target_table}")
        columns = [row[0] for row in cursor.fetchall() if row[0] != "LAST_UPDATED"]

        # Build merge statement
        set_clause = ", ".join([f"{col} = source.{col}" for col in columns if col != "ID"])
        insert_cols = ", ".join([*columns, "LAST_UPDATED"])
        values_clause = ", ".join([f"source.{col}" for col in columns] + ["CURRENT_TIMESTAMP()"])

        merge_sql = f"""
        MERGE INTO {target_table} target
        USING {temp_table} source
        ON target.ID = source.ID
        WHEN MATCHED THEN
            UPDATE SET {set_clause}, LAST_UPDATED = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT ({insert_cols})
            VALUES ({values_clause})
        """

        # Execute merge
        result = cursor.execute(merge_sql)
        conn.commit()

        # Get affected rows
        stats = result.fetchone()
        records_loaded = stats[0] if stats else 0

        return {
            "status": "success",
            "records_loaded": records_loaded,
            "target_table": target_table,
            "execution_time": time.time() - start_time,
        }

    except Exception as e:
        logger.exception(f"Error loading data: {e}")
        return {
            "status": "error",
            "records_loaded": 0,
            "target_table": target_table,
            "error_message": str(e),
            "execution_time": time.time() - start_time,
        }
    finally:
        if "conn" in locals() and conn:
            conn.close()
