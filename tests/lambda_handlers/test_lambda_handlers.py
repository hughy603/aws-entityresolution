"""Tests for Lambda handlers."""

import json
import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from aws_entity_resolution.lambda_handlers import (
    check_entity_resolution_job_handler,
    create_glue_table_handler,
    entity_resolution_handler,
    get_account_id,
    get_input_format,
    get_output_format,
    get_serde_info,
    notify_handler,
    snowflake_load_handler,
)

# Mock the factory import since it doesn't exist
# We'll patch the get_config function in the tests
with patch("aws_entity_resolution.config.factory.get_config"):
    pass


def test_get_input_format():
    """Test get_input_format function."""
    # Test CSV format
    assert get_input_format("csv") == "org.apache.hadoop.mapred.TextInputFormat"

    # Test JSON format
    assert get_input_format("json") == "org.apache.hadoop.mapred.TextInputFormat"

    # Test parquet format
    assert (
        get_input_format("parquet")
        == "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    )

    # Test unknown format - should default to text input format
    assert get_input_format("unknown") == "org.apache.hadoop.mapred.TextInputFormat"


def test_get_output_format():
    """Test get_output_format function."""
    # Test CSV format
    assert get_output_format("csv") == "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    # Test JSON format
    assert get_output_format("json") == "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    # Test parquet format
    assert (
        get_output_format("parquet")
        == "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    )

    # Test unknown format - should default to text output format
    assert (
        get_output_format("unknown") == "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
    )


def test_get_serde_info():
    """Test get_serde_info function."""
    # Test CSV format
    csv_serde = get_serde_info("csv")
    assert csv_serde["serializationLib"] == "org.apache.hadoop.hive.serde2.OpenCSVSerde"
    assert "separatorChar" in csv_serde["parameters"]

    # Test JSON format
    json_serde = get_serde_info("json")
    assert json_serde["serializationLib"] == "org.openx.data.jsonserde.JsonSerDe"

    # Test parquet format
    parquet_serde = get_serde_info("parquet")
    assert (
        parquet_serde["serializationLib"]
        == "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    )

    # Test unknown format - should raise ValueError
    with pytest.raises(ValueError):
        get_serde_info("unknown")


@pytest.fixture
def glue_client(aws_credentials, aws_mock):
    """Create a mocked Glue client."""
    return boto3.client("glue", region_name="us-west-2")


@pytest.fixture
def test_environment():
    """Set up environment variables for tests."""
    # Save original environment
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["CONFIG_S3_BUCKET"] = "test-config-bucket"
    os.environ["CONFIG_S3_KEY"] = "config/config.yaml"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@mock_aws
def test_create_glue_table_handler(glue_client, test_environment):
    """Test create_glue_table_handler function."""
    # Create a test database
    glue_client.create_database(
        DatabaseInput={
            "Name": "test-database",
        },
    )

    # Mock the configuration
    with patch("aws_entity_resolution.lambda_handlers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.aws.region = "us-west-2"
        mock_get_config.return_value = mock_config

        # Test event
        event = {
            "database": "test-database",
            "table_name": "test-table",
            "s3_path": "s3://test-bucket/data/",
            "schema": [
                {"name": "id", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string"},
            ],
            "format": "csv",
        }

        # Execute the handler
        with patch("boto3.client") as mock_client:
            mock_glue = MagicMock()
            mock_client.return_value = mock_glue

            response = create_glue_table_handler(event, None)

            # Verify response
            assert response["status"] == "success"
            assert response["database"] == "test-database"
            assert response["table_name"] == "test-table"

            # Verify glue client was called correctly
            mock_glue.create_table.assert_called_once()
            call_args = mock_glue.create_table.call_args[1]
            assert call_args["DatabaseName"] == "test-database"
            assert call_args["TableInput"]["Name"] == "test-table"


@mock_aws
def test_entity_resolution_handler(entity_resolution_client, s3_test_bucket):
    """Test entity_resolution_handler function."""
    # Unpack the fixture
    client, mocks = entity_resolution_client

    # Mock the configuration
    with patch("aws_entity_resolution.lambda_handlers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.aws.region = "us-west-2"
        mock_config.entity_resolution.schema_name = "test-schema"
        mock_config.entity_resolution.workflow_name = "test-workflow"
        mock_config.s3.bucket = s3_test_bucket
        mock_config.s3.prefix = "input/"
        mock_get_config.return_value = mock_config

        # Mock the EntityResolutionService
        with patch(
            "aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service:
            mock_er = MagicMock()
            mock_er.create_schema_mapping.return_value = "test-schema-arn"
            mock_er.create_matching_workflow.return_value = "test-workflow-arn"
            mock_er.start_matching_job.return_value = "test-job-id"
            mock_er_service.return_value = mock_er

            # Test event
            event = {
                "input_path": "s3://test-bucket/input/",
                "output_path": "s3://test-bucket/output/",
                "schema_attributes": [
                    {"name": "id", "type": "TEXT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"},
                ],
            }

            # Execute the handler
            response = entity_resolution_handler(event, None)

            # Verify response
            assert response["status"] == "success"
            assert response["job_id"] == "test-job-id"

            # Verify service calls
            assert mock_er.create_schema_mapping.called
            assert mock_er.create_matching_workflow.called
            assert mock_er.start_matching_job.called


def test_get_account_id():
    """Test get_account_id function."""
    # Mock STS client
    with patch("boto3.client") as mock_client:
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_client.return_value = mock_sts

        # Execute function
        account_id = get_account_id()

        # Verify result
        assert account_id == "123456789012"
        assert mock_sts.get_caller_identity.called


@mock_aws
def test_check_entity_resolution_job_handler(entity_resolution_client):
    """Test check_entity_resolution_job_handler function."""
    # Unpack the fixture
    client, mocks = entity_resolution_client

    # Mock the configuration
    with patch("aws_entity_resolution.lambda_handlers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.aws.region = "us-west-2"
        mock_get_config.return_value = mock_config

        # Mock the EntityResolutionService
        with patch(
            "aws_entity_resolution.lambda_handlers.EntityResolutionService"
        ) as mock_er_service:
            mock_er = MagicMock()
            mock_er.get_matching_job.return_value = {
                "jobId": "test-job-id",
                "jobStatus": "COMPLETED",
                "outputSourceConfig": {
                    "s3OutputConfig": {
                        "bucket": "test-bucket",
                        "prefix": "output/",
                    },
                },
            }
            mock_er_service.return_value = mock_er

            # Test event
            event = {
                "job_id": "test-job-id",
            }

            # Execute the handler
            response = check_entity_resolution_job_handler(event, None)

            # Verify response
            assert response["status"] == "success"
            assert response["job_status"] == "COMPLETED"
            assert response["output_path"] == "s3://test-bucket/output/"

            # Verify service calls
            assert mock_er.get_matching_job.called


@mock_aws
def test_snowflake_load_handler():
    """Test snowflake_load_handler function."""
    # Mock the configuration
    with patch("aws_entity_resolution.lambda_handlers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.aws.region = "us-west-2"
        mock_config.snowflake.account = "test-account"
        mock_config.snowflake.username = "test-user"
        mock_config.snowflake.password = "test-password"
        mock_config.snowflake.database = "TEST_DB"
        mock_config.snowflake.schema = "TEST_SCHEMA"
        mock_config.snowflake.warehouse = "TEST_WH"
        mock_config.snowflake.role = "TEST_ROLE"
        mock_get_config.return_value = mock_config

        # Mock the SnowflakeService
        with patch("aws_entity_resolution.lambda_handlers.SnowflakeService") as mock_sf_service:
            mock_sf = MagicMock()
            mock_sf.load_data_from_s3.return_value = {"rows_loaded": 100}
            mock_sf_service.return_value = mock_sf

            # Test event
            event = {
                "s3_path": "s3://test-bucket/output/",
                "table_name": "TEST_TABLE",
                "file_format": "CSV",
            }

            # Execute the handler
            response = snowflake_load_handler(event, None)

            # Verify response
            assert response["status"] == "success"
            assert response["rows_loaded"] == 100

            # Verify service calls
            assert mock_sf.load_data_from_s3.called
            mock_sf.load_data_from_s3.assert_called_with(
                s3_path="s3://test-bucket/output/",
                table_name="TEST_TABLE",
                file_format="CSV",
            )


@mock_aws
def test_notify_handler():
    """Test notify_handler function."""
    # Mock the configuration
    with patch("aws_entity_resolution.lambda_handlers.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.aws.region = "us-west-2"
        mock_config.notification.topic_arn = "arn:aws:sns:us-west-2:123456789012:test-topic"
        mock_get_config.return_value = mock_config

        # Mock the SNS client
        with patch("boto3.client") as mock_client:
            mock_sns = MagicMock()
            mock_sns.publish.return_value = {"MessageId": "test-message-id"}
            mock_client.return_value = mock_sns

            # Test event
            event = {
                "message": "Entity resolution process completed",
                "details": {
                    "job_id": "test-job-id",
                    "output_path": "s3://test-bucket/output/",
                    "rows_processed": 100,
                },
            }

            # Execute the handler
            response = notify_handler(event, None)

            # Verify response
            assert response["status"] == "success"
            assert response["message_id"] == "test-message-id"

            # Verify SNS client was called correctly
            mock_sns.publish.assert_called_once()
            call_args = mock_sns.publish.call_args[1]
            assert call_args["TopicArn"] == "arn:aws:sns:us-west-2:123456789012:test-topic"
            assert "message" in call_args["Message"]
            assert "job_id" in call_args["Message"]
