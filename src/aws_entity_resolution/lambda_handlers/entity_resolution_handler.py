"""Lambda handler for Entity Resolution operations.

This module contains Lambda handlers that work with AWS Entity Resolution
for schema retrieval and match processing.
"""

import json
import logging
from typing import Any

import boto3

from aws_entity_resolution.config.settings import get_settings
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import configure_logging, log_event

# Configure logging
logger = logging.getLogger(__name__)
configure_logging()


def _get_entity_resolution_client():
    """Get AWS Entity Resolution client.

    Returns:
        boto3 Entity Resolution client
    """
    settings = get_settings()
    return boto3.client("entityresolution", region_name=settings.aws.region)


@handle_exceptions("get_schema")
def get_schema(schema_name: str) -> dict[str, Any]:
    """Get Entity Resolution schema from AWS.

    Args:
        schema_name: Name of the schema to retrieve

    Returns:
        Schema definition as a dictionary

    Raises:
        Exception: If schema cannot be retrieved
    """
    client = _get_entity_resolution_client()

    try:
        response = client.get_schema(schemaName=schema_name)
        return {
            "schema_name": schema_name,
            "schema_arn": response.get("schemaArn", ""),
            "attributes": [
                {
                    "name": attr.get("name"),
                    "type": attr.get("type"),
                    "subtype": attr.get("subType", "NONE"),
                    "match_key": attr.get("matchKey", False),
                    "required": attr.get("required", False),
                }
                for attr in response.get("attributes", [])
            ],
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve schema {schema_name}: {e!s}")
        raise


@handle_exceptions("get_workflow")
def get_workflow(workflow_name: str) -> dict[str, Any]:
    """Get Entity Resolution workflow from AWS.

    Args:
        workflow_name: Name of the workflow to retrieve

    Returns:
        Workflow definition as a dictionary

    Raises:
        Exception: If workflow cannot be retrieved
    """
    client = _get_entity_resolution_client()

    try:
        response = client.get_matching_workflow(
            workflowName=workflow_name,
        )
        return {
            "workflow_name": workflow_name,
            "workflow_arn": response.get("workflowArn", ""),
            "role_arn": response.get("roleArn", ""),
            "schema_arn": response.get("inputSourceConfig", {}).get("inputSourceARN", ""),
            "creation_timestamp": response.get("creationTimestamp", ""),
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve workflow {workflow_name}: {e!s}")
        raise


@handle_exceptions("start_matching_job")
def start_matching_job(
    workflow_name: str,
    input_source_config: dict[str, Any],
    output_source_config: dict[str, Any],
) -> dict[str, Any]:
    """Start an Entity Resolution matching job.

    Args:
        workflow_name: Name of the matching workflow to use
        input_source_config: Configuration for input source
        output_source_config: Configuration for output destination

    Returns:
        Job information as a dictionary

    Raises:
        Exception: If job cannot be started
    """
    client = _get_entity_resolution_client()

    try:
        response = client.start_matching_job(
            workflowName=workflow_name,
            inputSourceConfig=input_source_config,
            outputSourceConfig=output_source_config,
        )

        job_id = response.get("jobId", "")
        log_event("matching_job_started", job_id=job_id, workflow=workflow_name)

        return {
            "job_id": job_id,
            "status": "STARTED",
            "workflow_name": workflow_name,
        }
    except Exception as e:
        logger.exception(f"Failed to start matching job for workflow {workflow_name}: {e!s}")
        raise


@handle_exceptions("get_matching_job")
def get_matching_job(job_id: str) -> dict[str, Any]:
    """Get information about an Entity Resolution matching job.

    Args:
        job_id: ID of the matching job to retrieve

    Returns:
        Job information as a dictionary

    Raises:
        Exception: If job information cannot be retrieved
    """
    client = _get_entity_resolution_client()

    try:
        response = client.get_matching_job(
            jobId=job_id,
        )

        return {
            "job_id": job_id,
            "status": response.get("jobStatus", "UNKNOWN"),
            "start_time": response.get("startTime", ""),
            "end_time": response.get("endTime", ""),
            "error": response.get("error", ""),
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve matching job {job_id}: {e!s}")
        raise


def schema_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for Entity Resolution schema operations.

    This handler provides schema information for Entity Resolution.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Response data for API Gateway or Step Functions
    """
    operation = event.get("operation", "GET_SCHEMA")
    schema_name = event.get("schema_name", "")

    if not schema_name:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "Missing schema_name parameter",
                }
            ),
        }

    if operation == "GET_SCHEMA":
        try:
            schema = get_schema(schema_name)
            return {
                "statusCode": 200,
                "body": json.dumps(schema),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": f"Unsupported operation: {operation}",
                }
            ),
        }


def workflow_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for Entity Resolution workflow operations.

    This handler manages Entity Resolution workflows.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Response data for API Gateway or Step Functions
    """
    operation = event.get("operation", "GET_WORKFLOW")
    workflow_name = event.get("workflow_name", "")

    if not workflow_name:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "Missing workflow_name parameter",
                }
            ),
        }

    if operation == "GET_WORKFLOW":
        try:
            workflow = get_workflow(workflow_name)
            return {
                "statusCode": 200,
                "body": json.dumps(workflow),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    elif operation == "START_MATCHING_JOB":
        input_source_config = event.get("input_source_config", {})
        output_source_config = event.get("output_source_config", {})

        if not input_source_config or not output_source_config:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Missing source configuration parameters",
                    }
                ),
            }

        try:
            job = start_matching_job(
                workflow_name=workflow_name,
                input_source_config=input_source_config,
                output_source_config=output_source_config,
            )
            return {
                "statusCode": 200,
                "body": json.dumps(job),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    elif operation == "GET_MATCHING_JOB":
        job_id = event.get("job_id", "")

        if not job_id:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Missing job_id parameter",
                    }
                ),
            }

        try:
            job = get_matching_job(job_id)
            return {
                "statusCode": 200,
                "body": json.dumps(job),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": str(e),
                    }
                ),
            }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": f"Unsupported operation: {operation}",
                }
            ),
        }
