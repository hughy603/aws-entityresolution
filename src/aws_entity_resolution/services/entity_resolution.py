"""Entity Resolution service.

This module provides functions for interacting with AWS Entity Resolution.
The infrastructure (Terraform/CloudFormation) is responsible for creating and managing
Entity Resolution resources, while this service is responsible for retrieving
and using those resources.
"""

import logging
from typing import Any

import boto3

from aws_entity_resolution.config.settings import get_settings

logger = logging.getLogger(__name__)


def get_schema(schema_name: str) -> dict[str, Any]:
    """Get Entity Resolution schema from AWS.

    Args:
        schema_name: Name of the schema

    Returns:
        Schema details
    """
    settings = get_settings()
    client = boto3.client("entityresolution", region_name=settings.aws.region)

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
                }
                for attr in response.get("attributes", [])
            ],
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve schema {schema_name}: {e}")
        return {"schema_name": schema_name, "error": str(e), "attributes": []}


def get_workflow(workflow_name: str) -> dict[str, Any]:
    """Get Entity Resolution workflow from AWS.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Workflow details
    """
    settings = get_settings()
    client = boto3.client("entityresolution", region_name=settings.aws.region)

    try:
        response = client.get_matching_workflow(workflowName=workflow_name)
        return {
            "workflow_name": workflow_name,
            "workflow_arn": response.get("workflowArn", ""),
            "schema_arn": response.get("inputSourceConfig", {}).get("inputSourceARN", ""),
        }
    except Exception as e:
        logger.exception(f"Failed to retrieve workflow {workflow_name}: {e}")
        return {"workflow_name": workflow_name, "error": str(e)}


def start_matching_job(
    workflow_name: str,
    input_source_config: dict[str, Any],
    output_source_config: dict[str, Any],
) -> dict[str, Any]:
    """Start a matching job.

    Args:
        workflow_name: Name of the workflow
        input_source_config: Input source configuration
        output_source_config: Output source configuration

    Returns:
        Job details
    """
    settings = get_settings()
    client = boto3.client("entityresolution", region_name=settings.aws.region)

    try:
        response = client.start_matching_job(
            workflowName=workflow_name,
            inputSourceConfig=input_source_config,
            outputSourceConfig=output_source_config,
        )
        return {
            "job_id": response.get("jobId", ""),
            "status": "STARTED",
        }
    except Exception as e:
        logger.exception(f"Failed to start matching job for workflow {workflow_name}: {e}")
        return {"error": str(e), "status": "FAILED"}


def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a matching job.

    Args:
        job_id: ID of the job

    Returns:
        Job status details
    """
    settings = get_settings()
    client = boto3.client("entityresolution", region_name=settings.aws.region)

    try:
        response = client.get_matching_job(jobId=job_id)
        return {
            "job_id": job_id,
            "status": response.get("jobStatus", "UNKNOWN"),
            "start_time": response.get("startTime", ""),
            "end_time": response.get("endTime", ""),
            "error": response.get("error", ""),
            "output_location": response.get("output", {}).get("s3Path", ""),
        }
    except Exception as e:
        logger.exception(f"Failed to get status for job {job_id}: {e}")
        return {"job_id": job_id, "error": str(e), "status": "UNKNOWN"}
