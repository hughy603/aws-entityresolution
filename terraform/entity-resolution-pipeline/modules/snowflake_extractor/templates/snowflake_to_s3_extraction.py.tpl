"""
Snowflake to S3 Entity Data Extraction
This script extracts entity data from Snowflake and saves it to S3 in a format suitable for AWS Entity Resolution.
"""

import sys
import json
import boto3
import logging
from datetime import datetime
from snowflake.connector import connect
from awsglue.utils import getResolvedOptions

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'snowflake_credentials_secret',
    'source_table',
    's3_bucket',
    's3_prefix'
])

def get_snowflake_credentials(secret_name):
    """Retrieve Snowflake credentials from AWS Secrets Manager."""
    logger.info(f"Retrieving Snowflake credentials from secret: {secret_name}")

    client = boto3.client('secretsmanager', region_name='${region}')

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        return json.loads(secret_string)
    except Exception as e:
        logger.error(f"Error retrieving Snowflake credentials: {str(e)}")
        raise

def snowflake_to_s3(credentials, source_table, s3_bucket, s3_prefix):
    """Extract data from Snowflake and upload to S3."""
    logger.info(f"Starting extraction from Snowflake table: {source_table}")

    # Generate timestamp for this extraction
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    s3_path = f"{s3_prefix}{timestamp}/"

    # Connect to Snowflake
    try:
        conn = connect(
            user=credentials['username'],
            password=credentials['password'],
            account=credentials['account'],
            warehouse=credentials['warehouse'],
            database=credentials['database'],
            schema=credentials['schema'],
            role=credentials['role']
        )
        cursor = conn.cursor()

        # Extract entity attributes
        entity_attributes = ${entity_attributes}
        attributes_str = ", ".join(entity_attributes)

        # Query the source table
        query = f"SELECT {attributes_str} FROM {source_table}"
        logger.info(f"Executing query: {query}")
        cursor.execute(query)

        # Fetch results and prepare for S3
        results = cursor.fetchall()
        column_names = [col[0].lower() for col in cursor.description]

        # Prepare data as JSON records
        records = []
        for row in results:
            record = {}
            for i, value in enumerate(row):
                if value is not None:
                    record[column_names[i]] = str(value)
            records.append(record)

        logger.info(f"Extracted {len(records)} records from Snowflake")

        # Write to S3
        s3_client = boto3.client('s3')
        s3_key = f"{s3_path}entity_data.json"

        # Format as newline-delimited JSON for Entity Resolution
        ndjson_data = "\n".join([json.dumps(record) for record in records])

        s3_client.put_object(
            Body=ndjson_data,
            Bucket=s3_bucket,
            Key=s3_key
        )

        logger.info(f"Successfully written data to s3://{s3_bucket}/{s3_key}")

        return {
            "status": "success",
            "record_count": len(records),
            "s3_bucket": s3_bucket,
            "s3_key": s3_key
        }

    except Exception as e:
        logger.error(f"Error in snowflake_to_s3: {str(e)}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """Main entry point for the Glue job."""
    try:
        # Get job parameters
        secret_name = args['snowflake_credentials_secret']
        source_table = args['source_table']
        s3_bucket = args['s3_bucket']
        s3_prefix = args['s3_prefix']

        # Get Snowflake credentials
        credentials = get_snowflake_credentials(secret_name)

        # Execute extraction
        result = snowflake_to_s3(credentials, source_table, s3_bucket, s3_prefix)

        # Log the result
        logger.info(f"Job completed successfully: {json.dumps(result)}")

    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
