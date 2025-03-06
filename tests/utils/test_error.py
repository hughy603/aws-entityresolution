"""Tests for error handling utilities."""

from typing import NoReturn
from unittest.mock import patch

import pytest

from aws_entity_resolution.utils.error import (
    BaseError,
    ConfigError,
    ServiceError,
    handle_exceptions,
)


def test_base_error():
    """Test BaseError class."""
    error = BaseError("Test error message")
    assert str(error) == "Test error message"
    assert error.message == "Test error message"


def test_service_error():
    """Test ServiceError class."""
    error = ServiceError("Service error message")
    assert str(error) == "Service error message"
    assert error.message == "Service error message"
    assert isinstance(error, BaseError)


def test_config_error():
    """Test ConfigError class."""
    error = ConfigError("Config error message")
    assert str(error) == "Config error message"
    assert error.message == "Config error message"
    assert isinstance(error, BaseError)


def test_handle_exceptions_no_error():
    """Test handle_exceptions decorator with no error."""

    @handle_exceptions("test_operation")
    def test_func() -> str:
        return "success"

    result = test_func()
    assert result == "success"


def test_handle_exceptions_with_value_error():
    """Test handle_exceptions decorator with ValueError."""

    @handle_exceptions("test_operation")
    def test_func() -> NoReturn:
        msg = "Test value error"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="Test value error"):
        test_func()


def test_handle_exceptions_with_unexpected_error():
    """Test handle_exceptions decorator with unexpected error."""

    class CustomError(Exception):
        """Custom error for testing."""

    @handle_exceptions("test_operation")
    def test_func() -> NoReturn:
        msg = "Test custom error"
        raise CustomError(msg)

    with pytest.raises(CustomError, match="Test custom error"):
        test_func()
