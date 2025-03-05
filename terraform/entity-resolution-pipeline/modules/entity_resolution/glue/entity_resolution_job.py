#!/usr/bin/env python3
"""Entity Resolution Processor Glue Job
This script processes entity data through AWS Entity Resolution using the aws_entity_resolution
package.
"""

import json
import logging
import sys

from awsglue.utils import getResolvedOptions

from aws_entity_resolution.config import (
    EntityResolutionConfig,
    S3Config,
    Settings,
)
from aws_entity_resolution.processor.processor import process_data

# Set up logging for Splunk
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - {"message": %(message)s}',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Glue job."""
    try:
        # Get job parameters
        args = getResolvedOptions(
            sys.argv,
            [
                "JOB_NAME",
                "s3_bucket",
                "input_s3_prefix",
                "output_s3_prefix",
                "workflow_name",
                "schema_name",
                "entity_attributes",
                "aws_region",
            ],
        )

        # Create settings object for the aws_entity_resolution package
        settings = Settings(
            aws_region=args["aws_region"],
            s3=S3Config(
                bucket=args["s3_bucket"], prefix=args["input_s3_prefix"], region=args["aws_region"]
            ),
            entity_resolution=EntityResolutionConfig(
                workflow_name=args["workflow_name"],
                schema_name=args["schema_name"],
                entity_attributes=args["entity_attributes"].split(","),
            ),
            source_table="dummy_value",  # Required by Settings but not used in this process
        )

        # Process data using the aws_entity_resolution package
        result = process_data(settings)

        # Log the result
        logger.info(
            json.dumps(
                {
                    "event": "entity_resolution_complete",
                    "status": result.status,
                    "job_id": result.job_id,
                    "input_records": result.input_records,
                    "matched_records": result.matched_records,
                    "output_location": f"s3://{result.s3_bucket}/{result.s3_key}",
                }
            )
        )

    except Exception as e:
        logger.error(json.dumps({"event": "entity_resolution_failed", "error": str(e)}))
        raise


if __name__ == "__main__":
    main()
