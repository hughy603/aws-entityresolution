"""Tests for the database.py module."""

from unittest.mock import MagicMock

import pytest
from snowflake.connector.cursor import SnowflakeCursor

from aws_entity_resolution.extractor.database import execute_query


@pytest.fixture
def mock_snowflake_cursor() -> MagicMock:
    """Create a mock Snowflake cursor for testing."""
    cursor = MagicMock(spec=SnowflakeCursor)
    cursor.fetchall.return_value = [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
    ]
    return cursor


def test_execute_query_without_params(mock_snowflake_cursor: MagicMock) -> None:
    """Test execute_query with a basic query and no parameters."""
    query = "SELECT * FROM users"

    result = execute_query(mock_snowflake_cursor, query)

    mock_snowflake_cursor.execute.assert_called_once_with(query, ())
    mock_snowflake_cursor.fetchall.assert_called_once()
    assert len(result) == 2
    assert result[0]["name"] == "John Doe"
    assert result[1]["email"] == "jane@example.com"


def test_execute_query_with_params(mock_snowflake_cursor: MagicMock) -> None:
    """Test execute_query with parameters."""
    query = "SELECT * FROM users WHERE id = %s"
    params = (1,)

    result = execute_query(mock_snowflake_cursor, query, params)

    mock_snowflake_cursor.execute.assert_called_once_with(query, params)
    mock_snowflake_cursor.fetchall.assert_called_once()
    assert len(result) == 2  # Using the mock's return value


def test_execute_query_no_results(mock_snowflake_cursor: MagicMock) -> None:
    """Test execute_query when no results are found."""
    mock_snowflake_cursor.fetchall.return_value = []
    query = "SELECT * FROM users WHERE id = 999"

    result = execute_query(mock_snowflake_cursor, query)

    mock_snowflake_cursor.execute.assert_called_once_with(query, ())
    mock_snowflake_cursor.fetchall.assert_called_once()
    assert len(result) == 0
    assert isinstance(result, list)


def test_execute_query_error_handling(mock_snowflake_cursor: MagicMock) -> None:
    """Test execute_query error handling."""
    mock_snowflake_cursor.execute.side_effect = Exception("Database error")
    query = "INVALID SQL QUERY"

    with pytest.raises(Exception) as exc_info:
        execute_query(mock_snowflake_cursor, query)

    assert "Database error" in str(exc_info.value)
    mock_snowflake_cursor.execute.assert_called_once_with(query, ())
    mock_snowflake_cursor.fetchall.assert_not_called()
