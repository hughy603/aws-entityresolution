import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import boto3
import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from moto import mock_aws

# Try to import from moto v5
try:
    # Check if we're using moto v5+ which has the mock_aws decorator
    from moto import __version__ as moto_version

    USING_MOTO_V5 = int(moto_version.split(".")[0]) >= 5
except (ImportError, AttributeError, ValueError):
    USING_MOTO_V5 = True  # Default to assuming v5+

# Get package name dynamically
import pathlib

from dotenv import load_dotenv

package_name = pathlib.Path(__file__).parent.parent.joinpath("src").name


@pytest.fixture
def aws_credentials():
    """Set up mock AWS credentials for tests."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_REGION"] = "us-west-2"

    yield

    # Clean up
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    os.environ.pop("AWS_SECURITY_TOKEN", None)
    os.environ.pop("AWS_SESSION_TOKEN", None)
    os.environ.pop("AWS_DEFAULT_REGION", None)
    os.environ.pop("AWS_REGION", None)


# Use the new mock_aws decorator for all AWS services
@pytest.fixture
def aws_mock():
    """Mock all AWS services."""
    with mock_aws():
        yield


# Enhanced AWS Service Fixtures
@pytest.fixture
def s3_client(aws_credentials, aws_mock):
    """Create a mocked S3 client."""
    return boto3.client("s3", region_name="us-west-2")


@pytest.fixture
def s3_resource(aws_credentials, aws_mock):
    """Create a mocked S3 resource."""
    return boto3.resource("s3", region_name="us-west-2")


@pytest.fixture
def dynamodb_client(aws_credentials, aws_mock):
    """Create a mocked DynamoDB client."""
    return boto3.client("dynamodb", region_name="us-west-2")


@pytest.fixture
def dynamodb_resource(aws_credentials, aws_mock):
    """Create a mocked DynamoDB resource."""
    return boto3.resource("dynamodb", region_name="us-west-2")


@pytest.fixture
def sqs_client(aws_credentials, aws_mock):
    """Create a mocked SQS client."""
    return boto3.client("sqs", region_name="us-west-2")


@pytest.fixture
def sqs_resource(aws_credentials, aws_mock):
    """Create a mocked SQS resource."""
    return boto3.resource("sqs", region_name="us-west-2")


@pytest.fixture
def lambda_client(aws_credentials, aws_mock):
    """Create a mocked Lambda client."""
    return boto3.client("lambda", region_name="us-west-2")


@pytest.fixture
def sns_client(aws_credentials, aws_mock):
    """Create a mocked SNS client."""
    return boto3.client("sns", region_name="us-west-2")


@pytest.fixture
def cloudwatch_client(aws_credentials, aws_mock):
    """Create a mocked CloudWatch client."""
    return boto3.client("cloudwatch", region_name="us-west-2")


@pytest.fixture
def iam_client(aws_credentials, aws_mock):
    """Create a mocked IAM client."""
    return boto3.client("iam", region_name="us-west-2")


@pytest.fixture
def sts_client(aws_credentials, aws_mock):
    """Create a mocked STS client."""
    return boto3.client("sts", region_name="us-west-2")


@pytest.fixture
def ssm_client(aws_credentials, aws_mock):
    """Create a mocked SSM client."""
    return boto3.client("ssm", region_name="us-west-2")


@pytest.fixture
def mock_snowflake_cursor():
    """Create a mock Snowflake cursor."""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.description = []
    return cursor


@pytest.fixture
def mock_snowflake_connection(mock_snowflake_cursor):
    """Create a mock Snowflake connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_snowflake_cursor
    return conn


@pytest.fixture
def mock_snowflake(mock_snowflake_connection):
    """Set up mock for Snowflake connector."""
    with patch("snowflake.connector.connect") as mock_connect:
        mock_connect.return_value = mock_snowflake_connection
        yield {
            "connect": mock_connect,
            "connection": mock_snowflake_connection,
            "cursor": mock_snowflake_connection.cursor(),
        }


@pytest.fixture
def mock_snowflake_with_data(mock_snowflake):
    """Set up mock for Snowflake connector with sample data."""
    cursor = mock_snowflake["cursor"]
    cursor.fetchall.return_value = [
        (1, "John Doe", "john@example.com"),
        (2, "Jane Smith", "jane@example.com"),
    ]
    cursor.description = [
        ("ID", "NUMBER", None, None, None, None, None),
        ("NAME", "TEXT", None, None, None, None, None),
        ("EMAIL", "TEXT", None, None, None, None, None),
    ]
    return mock_snowflake


@pytest.fixture(autouse=True)
def patch_snowflake_for_all_tests(mock_snowflake):
    """Patch Snowflake connector for all tests."""


def pytest_configure(config: Config) -> None:
    """Configure pytest with custom markers, AWS mocks, and load test environment variables."""
    # Load test environment variables
    load_dotenv(".env.test")

    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )

    # Configure moto
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
    os.environ.setdefault("AWS_SESSION_TOKEN", "testing")


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """Automatically mark tests as slow based on patterns."""
    for item in items:
        # Mark integration tests as slow
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Mark specific test patterns as slow
        slow_patterns = [
            "test_load_records_",  # Record loading tests
            "test_start_entity_resolution_job",  # AWS Entity Resolution job tests
            "test_wait_for_matching_job_",  # Job waiting tests
            "test_run_pipeline_",  # Full pipeline tests
        ]

        for pattern in slow_patterns:
            if pattern in item.nodeid:
                item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def mock_env_vars() -> Generator[None, None, None]:
    """Mock environment variables for testing."""
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ.update(
        {
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "SNOWFLAKE_ACCOUNT": "test_account",
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_PASSWORD": "test_password",
            "SNOWFLAKE_WAREHOUSE": "test_warehouse",
            "SNOWFLAKE_DATABASE": "test_database",
            "SNOWFLAKE_SCHEMA": "test_schema",
            "AWS_ENTITY_RESOLUTION_SCHEMA_NAME": "test_schema",
            "AWS_ENTITY_RESOLUTION_MATCHING_WORKFLOW_NAME": "test_workflow",
            "AWS_ENTITY_RESOLUTION_MATCHING_WORKFLOW_ROLE_ARN": "arn:aws:iam::123456789012:role/test-role",
            "AWS_ENTITY_RESOLUTION_MATCHING_WORKFLOW_BUCKET": "test-bucket",
            "AWS_ENTITY_RESOLUTION_MATCHING_WORKFLOW_PREFIX": "test/prefix/",
        },
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def s3_mock(aws_credentials, aws_mock):
    """Set up an S3 bucket for tests."""
    s3 = boto3.client("s3", region_name="us-west-2")
    # Create test bucket
    s3.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    return s3


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.aws_region = "us-west-2"
    settings.aws_access_key_id = "testing"
    settings.aws_secret_access_key = "testing"

    # Set up source and target tables
    settings.source_table = "test_source"
    settings.target_table = "test_target"

    # Set up snowflake_source
    settings.snowflake_source = MagicMock()
    settings.snowflake_source.account = "test_account"
    settings.snowflake_source.username = "test_user"
    settings.snowflake_source.password = "test_password"
    settings.snowflake_source.warehouse = "test_warehouse"
    settings.snowflake_source.database = "test_db"
    settings.snowflake_source.schema = "test_schema"

    # Set up snowflake_target
    settings.snowflake_target = MagicMock()
    settings.snowflake_target.account = "test_account"
    settings.snowflake_target.username = "test_user"
    settings.snowflake_target.password = "test_password"
    settings.snowflake_target.warehouse = "test_warehouse"
    settings.snowflake_target.database = "test_db"
    settings.snowflake_target.schema = "test_schema"

    # Set up S3
    settings.s3 = MagicMock()
    settings.s3.bucket = "test-bucket"
    settings.s3.prefix = "test-prefix"
    settings.s3.region = "us-west-2"

    # Set up entity_resolution
    settings.entity_resolution = MagicMock()
    settings.entity_resolution.workflow_name = "test-workflow"
    settings.entity_resolution.schema_name = "test-schema"
    settings.entity_resolution.entity_attributes = ["id", "name", "email"]

    return settings


@pytest.fixture
def entity_resolution_client(aws_credentials, aws_mock):
    """Create a mocked Entity Resolution client with better support."""
    client = boto3.client("entityresolution", region_name="us-west-2")

    # Add custom mocking for entity resolution methods if needed
    # This overrides moto's limited support for Entity Resolution service

    # Mock schema creation
    with patch.object(
        client,
        "create_schema_mapping",
        return_value={
            "schemaArn": "arn:aws:entityresolution:us-west-2:123456789012:schemamapping/test-schema",
            "createdAt": "2023-01-01T00:00:00Z",
        },
    ) as mock_create_schema:
        # Mock list schemas
        with patch.object(
            client,
            "list_schema_mappings",
            return_value={
                "schemaMappings": [
                    {
                        "schemaName": "test-schema",
                        "schemaArn": "arn:aws:entityresolution:us-west-2:123456789012:schemamapping/test-schema",
                        "createdAt": "2023-01-01T00:00:00Z",
                    },
                ],
            },
        ) as mock_list_schemas:
            # Mock create matching workflow
            with patch.object(
                client,
                "create_matching_workflow",
                return_value={
                    "workflowArn": "arn:aws:entityresolution:us-west-2:123456789012:matchingworkflow/test-workflow",
                    "createdAt": "2023-01-01T00:00:00Z",
                },
            ) as mock_create_workflow:
                # Mock start matching job
                with patch.object(
                    client,
                    "start_matching_job",
                    return_value={
                        "jobId": "test-job-id",
                        "jobArn": "arn:aws:entityresolution:us-west-2:123456789012:matchingjob/test-job-id",
                    },
                ) as mock_start_job:
                    # Mock get matching job
                    with patch.object(
                        client,
                        "get_matching_job",
                        return_value={
                            "jobId": "test-job-id",
                            "jobStatus": "COMPLETED",
                            "createdAt": "2023-01-01T00:00:00Z",
                            "outputSourceConfig": {
                                "s3OutputConfig": {
                                    "bucket": "test-bucket",
                                    "prefix": "output/",
                                },
                            },
                        },
                    ) as mock_get_job:
                        yield (
                            client,
                            {
                                "create_schema": mock_create_schema,
                                "list_schemas": mock_list_schemas,
                                "create_workflow": mock_create_workflow,
                                "start_job": mock_start_job,
                                "get_job": mock_get_job,
                            },
                        )


@pytest.fixture
def s3_test_bucket(s3_client):
    """Create a test S3 bucket using moto."""
    bucket_name = "test-entity-resolution-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Create test files
    s3_client.put_object(
        Bucket=bucket_name,
        Key="test-data/sample.csv",
        Body="id,name,email\n1,Test User,test@example.com",
    )

    s3_client.put_object(
        Bucket=bucket_name,
        Key="config/schema.json",
        Body='{"schemaName":"test-schema","attributes":[{"attributeName":"id","attributeType":"TEXT"},{"attributeName":"name","attributeType":"TEXT"},{"attributeName":"email","attributeType":"TEXT"}]}',
    )

    return bucket_name
