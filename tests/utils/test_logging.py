"""Tests for logging utilities."""

import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from aws_entity_resolution.utils.logging import (
    get_logger,
    log_event,
    setup_structured_logging,
)


def test_get_logger():
    """Test get_logger function."""
    logger = get_logger("test_module")
    assert logger.name == "test_module"
    assert isinstance(logger, logging.Logger)


def test_get_logger_with_custom_level():
    """Test get_logger function with custom log level."""
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        logger = get_logger("test_module")
        assert logger.level == logging.DEBUG


def test_log_event():
    """Test log_event function."""
    mock_logger = MagicMock()

    with patch("logging.getLogger", return_value=mock_logger):
        log_event("test_event", param1="value1", param2=123)

    mock_logger.info.assert_called_once()
    log_message = mock_logger.info.call_args[0][0]
    assert '"event": "test_event"' in log_message
    assert '"param1": "value1"' in log_message
    assert '"param2": 123' in log_message


def test_log_event_with_dict():
    """Test log_event function with dictionary data."""
    mock_logger = MagicMock()

    with patch("logging.getLogger", return_value=mock_logger):
        log_event("test_event", data={"key1": "value1", "key2": 123})

    mock_logger.info.assert_called_once()
    log_message = mock_logger.info.call_args[0][0]
    assert '"event": "test_event"' in log_message
    assert '"data": ' in log_message


def test_setup_structured_logging():
    """Test setup_structured_logging function."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_logger.handlers = []

        result = setup_structured_logging()

        assert result == mock_logger
        assert mock_logger.addHandler.called
        assert mock_logger.setLevel.called
