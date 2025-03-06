"""Snowflake service for AWS Entity Resolution.

This module provides a service class for interacting with Snowflake databases.
It handles connection management, query execution, and data retrieval.
"""

import logging
from types import TracebackType
from typing import Any, Optional, Union

import snowflake.connector
from snowflake.connector.cursor import SnowflakeCursor
from snowflake.connector.errors import Error as SnowflakeError
from snowflake.connector.errors import InterfaceError

from aws_entity_resolution.config import Settings, SnowflakeConfig

logger = logging.getLogger(__name__)


class SnowflakeService:
    """Service for interacting with Snowflake databases.

    This service provides methods for connecting to Snowflake, executing queries,
    and retrieving data. It supports both source and target database connections
    based on configuration.

    Attributes:
        settings: Application configuration settings
        use_target: Whether to use target database configuration
        connection: Active Snowflake connection
        cursor: Active Snowflake cursor
    """

    def __init__(self: "SnowflakeService", settings: Settings, use_target: bool = False) -> None:
        """Initialize the Snowflake service.

        Args:
            settings: Application configuration settings
            use_target: Whether to use target database configuration (default: False)
        """
        self.settings = settings
        self.use_target = use_target
        self.connection: Optional[snowflake.connector.SnowflakeConnection] = None
        self.cursor: Optional[SnowflakeCursor] = None

    @property
    def config(self: "SnowflakeService") -> SnowflakeConfig:
        """Get the appropriate Snowflake configuration.

        Returns:
            The Snowflake configuration for either source or target database
        """
        return self.settings.snowflake_target if self.use_target else self.settings.snowflake_source

    def connect(self: "SnowflakeService") -> snowflake.connector.SnowflakeConnection:
        """Connect to Snowflake database.

        Returns:
            Active Snowflake connection

        Raises:
            InterfaceError: If connection fails due to invalid credentials
            SnowflakeError: If connection fails for other reasons
        """
        if self.connection is not None and not self.connection.is_closed():
            return self.connection

        try:
            logger.info(
                "Connecting to Snowflake account: %s, database: %s, schema: %s",
                self.config.account,
                self.config.database,
                self.config.schema,
            )
            self.connection = snowflake.connector.connect(
                user=self.config.username,
                password=self.config.password,
                account=self.config.account,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.role,
            )
        except InterfaceError as e:
            logger.exception("Failed to connect to Snowflake: %s", str(e))
            raise
        except SnowflakeError as e:
            logger.exception("Snowflake error during connection: %s", str(e))
            raise
        else:
            logger.info("Connected to Snowflake")
            return self.connection

    def disconnect(self: "SnowflakeService") -> None:
        """Close Snowflake connection and cursor."""
        try:
            if self.cursor is not None:
                self.cursor.close()
        except SnowflakeError as e:
            logger.warning("Error closing Snowflake cursor: %s", str(e))
        finally:
            self.cursor = None

        try:
            if self.connection is not None:
                self.connection.close()
        except SnowflakeError as e:
            logger.warning("Error closing Snowflake connection: %s", str(e))
        finally:
            self.connection = None

    def execute_query(
        self: "SnowflakeService",
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries.

        Args:
            query: SQL query to execute
            params: Query parameters (default: None)

        Returns:
            List of dictionaries containing query results

        Raises:
            SnowflakeError: If query execution fails
        """
        if self.connection is None:
            self.connect()

        try:
            self.cursor = self.connection.cursor()
            self.cursor.execute(query, params)

            # Get column names from cursor description
            columns = [col[0] for col in self.cursor.description]

            # Convert results to list of dictionaries
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row, strict=False)))

        except SnowflakeError as e:
            logger.exception("Snowflake error during query execution: %s", str(e))
            raise
        else:
            logger.info("Query executed successfully")
            return results

    def execute_statement(
        self: "SnowflakeService",
        statement: str,
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """Execute a SQL statement that doesn't return results.

        Args:
            statement: SQL statement to execute
            params: Statement parameters (default: None)

        Returns:
            Number of rows affected

        Raises:
            SnowflakeError: If statement execution fails
        """
        if self.connection is None:
            self.connect()

        try:
            self.cursor = self.connection.cursor()
            self.cursor.execute(statement, params)
            return self.cursor.rowcount
        except SnowflakeError as e:
            logger.exception("Snowflake error during statement execution: %s", str(e))
            raise

    def fetch_table_data(
        self: "SnowflakeService",
        table_name: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Fetch data from a table.

        Args:
            table_name: Name of the table to query
            limit: Maximum number of rows to return (default: None)

        Returns:
            List of dictionaries containing table data

        Raises:
            SnowflakeError: If query execution fails
        """
        query = f"SELECT * FROM {table_name}"
        if limit is not None:
            query += f" LIMIT {limit}"

        return self.execute_query(query)

    def table_exists(self: "SnowflakeService", table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name: Name of the table to check

        Returns:
            True if the table exists, False otherwise
        """
        try:
            query = f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{self.config.schema}'
            AND table_name = '{table_name}'
            """
            result = self.execute_query(query)
            return result[0]["COUNT(*)"] > 0
        except SnowflakeError as e:
            logger.exception("Error checking if table exists: %s", str(e))
            return False

    def create_table(self: "SnowflakeService", table_name: str, columns: list[str]) -> None:
        """Create a new table.

        Args:
            table_name: Name of the table to create
            columns: List of column definitions (e.g., ["id INTEGER", "name VARCHAR"])

        Raises:
            SnowflakeError: If table creation fails
        """
        columns_str = ", ".join(columns)
        statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        self.execute_statement(statement)

    def insert_data(self: "SnowflakeService", table_name: str, data: list[dict[str, Any]]) -> int:
        """Insert data into a Snowflake table.

        Args:
            table_name: Name of the table to insert data into
            data: List of dictionaries containing data to insert

        Returns:
            Number of rows inserted

        Raises:
            SnowflakeError: If the insert operation fails
        """
        if not data:
            return 0

        # Get column names from the first row
        columns = list(data[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        column_names = ", ".join([f'"{col}"' for col in columns])

        # Prepare the insert statement
        insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'

        # Execute the insert for each row
        rows_inserted = 0
        with self.connect():
            for row in data:
                self.cursor.execute(insert_sql, row)
                rows_inserted += self.cursor.rowcount

        return rows_inserted

    def load_data_from_s3(
        self: "SnowflakeService",
        s3_path: str,
        target_table: str,
        file_format: str = "CSV",
    ) -> int:
        """Load data from S3 to Snowflake.

        Args:
            s3_path: S3 URI of the data to load
            target_table: Name of the target table
            file_format: File format of the data (default: CSV)

        Returns:
            Number of rows loaded

        Raises:
            SnowflakeError: If the load operation fails
        """
        # Parse S3 URI
        s3_parts = s3_path.replace("s3://", "").split("/")
        bucket = s3_parts[0]
        prefix = "/".join(s3_parts[1:])

        # Create file format if it doesn't exist
        file_format_name = f"{file_format.lower()}_format"
        create_format_sql = f"""
        CREATE FILE FORMAT IF NOT EXISTS {file_format_name}
        TYPE = '{file_format}'
        FIELD_DELIMITER = ','
        SKIP_HEADER = 1
        NULL_IF = ('NULL', 'null', '')
        FIELD_OPTIONALLY_ENCLOSED_BY = '"'
        """

        # Create stage if it doesn't exist
        stage_name = f"entity_resolution_stage_{bucket.replace('-', '_')}"
        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS {stage_name}
        URL = 's3://{bucket}'
        FILE_FORMAT = {file_format_name}
        """

        # Load data from S3 to Snowflake
        copy_sql = f"""
        COPY INTO "{target_table}"
        FROM @{stage_name}/{prefix}
        FILE_FORMAT = (FORMAT_NAME = {file_format_name})
        ON_ERROR = 'CONTINUE'
        """

        with self.connect():
            # Create file format and stage
            self.cursor.execute(create_format_sql)
            self.cursor.execute(create_stage_sql)

            # Execute the COPY command
            self.cursor.execute(copy_sql)

            # Get the number of rows loaded
            result = self.cursor.fetchone()
            return result[0] if result else 0

    def __enter__(self: "SnowflakeService") -> "SnowflakeService":
        """Enter context manager.

        Returns:
            Self for use in context manager
        """
        self.connect()
        return self

    def __exit__(
        self: "SnowflakeService",
        exc_type: Optional[type[Exception]],
        exc_val: Optional[Exception],
        exc_tb: Union[TracebackType, None],
    ) -> None:
        """Exit context manager and close connections."""
        self.disconnect()
