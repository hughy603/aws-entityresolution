"""Example of secure database query handling."""

from typing import Any, Optional

from snowflake.connector.cursor import SnowflakeCursor


def execute_query(
    cursor: SnowflakeCursor, query: str, params: tuple[Any, ...] | None = None
) -> list[dict[str, Any]]:
    """Execute a query securely using parameterized queries.

    Args:
        cursor: Snowflake cursor
        query: SQL query with parameter placeholders
        params: Query parameters

    Returns:
        List of records as dictionaries
    """
    cursor.execute(query, params or ())
    return cursor.fetchall()
