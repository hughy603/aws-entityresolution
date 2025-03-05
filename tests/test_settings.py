"""Tests for the settings module."""

import os
from unittest.mock import patch

from aws_entity_resolution.config.settings import get_password


def test_get_password_from_env() -> None:
    """Test retrieving password from environment variable."""
    with patch.dict(os.environ, {"DB_PASSWORD": "test-password"}):
        password = get_password()
        assert password == "test-password"


def test_get_password_missing_env() -> None:
    """Test retrieving password when environment variable is not set."""
    with patch.dict(os.environ, clear=True):
        password = get_password()
        assert password is None
