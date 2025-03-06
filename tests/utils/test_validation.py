"""Tests for validation utilities."""

from unittest.mock import MagicMock, patch

import pytest

from aws_entity_resolution.utils.validation import (
    validate_enum,
    validate_required,
    validate_s3_path,
)


def test_validate_s3_path_valid():
    """Test validate_s3_path with valid paths."""
    # Valid S3 URI
    assert validate_s3_path("s3://bucket/path/to/file.csv") is True
    # Valid bucket/key format
    assert validate_s3_path("bucket/path/to/file.csv") is True


def test_validate_s3_path_invalid():
    """Test validate_s3_path with invalid paths."""
    # Invalid S3 URI
    assert validate_s3_path("not-an-s3-uri") is False
    assert validate_s3_path("http://bucket/path") is False
    assert validate_s3_path("s3:/bucket/path") is False


def test_validate_required_valid():
    """Test validate_required with valid values."""
    # These should not raise exceptions
    validate_required("value", "test_string")
    validate_required(123, "test_number")
    validate_required([1, 2, 3], "test_list")
    validate_required({"key": "value"}, "test_dict")


def test_validate_required_invalid():
    """Test validate_required with invalid values."""
    # None value
    with pytest.raises(ValueError, match="test_none is required and cannot be None"):
        validate_required(None, "test_none")

    # Empty string
    with pytest.raises(ValueError, match="test_empty_string is required and cannot be empty"):
        validate_required("", "test_empty_string")

    # Whitespace string
    with pytest.raises(ValueError, match="test_whitespace is required and cannot be empty"):
        validate_required("   ", "test_whitespace")

    # Empty list
    with pytest.raises(ValueError, match="test_empty_list is required and cannot be empty"):
        validate_required([], "test_empty_list")

    # Empty dict
    with pytest.raises(ValueError, match="test_empty_dict is required and cannot be empty"):
        validate_required({}, "test_empty_dict")


def test_validate_enum_valid():
    """Test validate_enum with valid values."""
    # These should not raise exceptions
    validate_enum("value1", ["value1", "value2", "value3"], "test_enum")
    validate_enum(1, [1, 2, 3], "test_enum")


def test_validate_enum_invalid():
    """Test validate_enum with invalid values."""
    # Invalid enum value
    with pytest.raises(ValueError, match="test_enum must be one of"):
        validate_enum("value4", ["value1", "value2", "value3"], "test_enum")

    # Invalid enum type
    with pytest.raises(ValueError, match="test_enum must be one of"):
        validate_enum(4, [1, 2, 3], "test_enum")
