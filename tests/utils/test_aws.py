"""Tests for AWS utilities."""

from unittest.mock import MagicMock, patch

import pytest

from aws_entity_resolution.utils.aws import (
    get_aws_client,
    get_aws_resource,
)


def test_get_aws_client():
    """Test get_aws_client function."""
    with patch("boto3.client") as mock_client:
        # Test with default parameters
        client = get_aws_client("s3")
        mock_client.assert_called_once_with("s3", region_name=None)

        # Test with region
        mock_client.reset_mock()
        client = get_aws_client("s3", region_name="us-west-2")
        mock_client.assert_called_once_with("s3", region_name="us-west-2")


def test_get_aws_resource():
    """Test get_aws_resource function."""
    with patch("boto3.resource") as mock_resource:
        # Test with default parameters
        resource = get_aws_resource("s3")
        mock_resource.assert_called_once_with("s3", region_name=None)

        # Test with region
        mock_resource.reset_mock()
        resource = get_aws_resource("s3", region_name="us-west-2")
        mock_resource.assert_called_once_with("s3", region_name="us-west-2")
