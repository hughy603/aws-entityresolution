"""
S3 to Snowflake Loader for Entity Resolution
This script loads resolved entity data from S3 back to Snowflake to create golden records.
"""

import sys
import json
import boto3
import logging
import uuid
from datetime import datetime
from awsglue.utils import getResolvedOptions
from snowflake.connector import connect

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
    'target_table',
    's3_bucket',
    's3_output_prefix'
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

def find_latest_output_path(s3_client, bucket, prefix):
    """Find the latest Entity Resolution output path in S3."""
    logger.info(f"Finding latest output path in s3://{bucket}/{prefix}")

    # List objects with the given prefix
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix,
        Delimiter='/'
    )

    if 'CommonPrefixes' not in response:
        logger.error(f"No output data found in s3://{bucket}/{prefix}")
        return None

    # Get all date-based prefixes and sort them
    prefixes = [p['Prefix'] for p in response['CommonPrefixes']]
    prefixes.sort(reverse=True)

    if not prefixes:
        logger.error(f"No timestamped directories found in s3://{bucket}/{prefix}")
        return None

    latest_prefix = prefixes[0]

    # Find the output data files within the latest prefix
    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=latest_prefix
    )

    if 'Contents' not in response or not response['Contents']:
        logger.error(f"No files found in s3://{bucket}/{latest_prefix}")
        return None

    # Filter for match results files
    match_file_keys = [obj['Key'] for obj in response['Contents']
                       if obj['Key'].endswith('match-result.json') or
                          obj['Key'].endswith('output.json')]

    if not match_file_keys:
        logger.error(f"No match result files found in s3://{bucket}/{latest_prefix}")
        return None

    logger.info(f"Found match result files: {match_file_keys}")
    return (latest_prefix, match_file_keys)

def read_match_results(s3_client, bucket, file_keys):
    """Read match results from S3."""
    logger.info(f"Reading match results from S3")

    all_records = []

    for key in file_keys:
        try:
            response = s3_client.get_object(
                Bucket=bucket,
                Key=key
            )

            content = response['Body'].read().decode('utf-8')

            # Check if it's newline-delimited JSON
            if '\n' in content:
                # Process each line as a separate JSON object
                for line in content.strip().split('\n'):
                    if line:
                        record = json.loads(line)
                        all_records.append(record)
            else:
                # Single JSON array
                records = json.loads(content)
                if isinstance(records, list):
                    all_records.extend(records)
                else:
                    all_records.append(records)

            logger.info(f"Read {len(all_records)} records from {key}")

        except Exception as e:
            logger.error(f"Error reading file {key}: {str(e)}")
            raise

    return all_records

def process_match_results(records):
    """Process match results to prepare for Snowflake loading."""
    logger.info(f"Processing {len(records)} match results")

    processed_records = []

    for record in records:
        # Entity Resolution typically adds entityId or matchId to indicate grouped entities
        entity_id = record.get('entityId') or record.get('matchId') or record.get('MATCH_ID')

        if not entity_id:
            # Skip records without entity ID
            continue

        # Generate a unique ID for this record
        record_id = str(uuid.uuid4())

        # Determine if this is the golden record (typically the first in group)
        # This logic can be customized based on your specific Entity Resolution output format
        is_golden = record.get('isGoldenRecord', False) or record.get('IS_GOLDEN_RECORD', False)

        # Extract original source ID if available
        source_id = record.get('sourceId') or record.get('SOURCE_ID') or record.get('id') or record.get('ID')

        processed_record = {
            'ID': record_id,
            'ENTITY_ID': entity_id,
            'SOURCE_ID': source_id,
            'IS_GOLDEN_RECORD': is_golden
        }

        # Add entity attributes if they exist in the record
        entity_attributes = ${entity_attributes}
        for attr in entity_attributes:
            # Try different case versions of the attribute name
            attr_value = record.get(attr) or record.get(attr.lower()) or record.get(attr.upper())
            processed_record[attr.upper()] = attr_value

        processed_records.append(processed_record)

    logger.info(f"Processed {len(processed_records)} records")
    return processed_records

def load_to_snowflake(credentials, target_table, records):
    """Load processed records to Snowflake."""
    if not records:
        logger.info("No records to load to Snowflake")
        return 0

    logger.info(f"Loading {len(records)} records to Snowflake table: {target_table}")

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

        # Prepare insert statement
        columns = list(records[0].keys())
        columns_str = ", ".join(columns)
        values_placeholders = ", ".join(["%s"] * len(columns))

        insert_query = f"INSERT INTO {target_table} ({columns_str}) VALUES ({values_placeholders})"
        logger.info(f"Insert query: {insert_query}")

        # Extract values in the same order as columns
        records_values = []
        for record in records:
            record_values = [record.get(col) for col in columns]
            records_values.append(record_values)

        # Execute batch insert
        cursor.executemany(insert_query, records_values)

        # Commit the transaction
        conn.commit()

        logger.info(f"Successfully loaded {len(records)} records to Snowflake")
        return len(records)

    except Exception as e:
        logger.error(f"Error loading to Snowflake: {str(e)}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """Main entry point for the Glue job."""
    try:
        # Get job parameters
        secret_name = args['snowflake_credentials_secret']
        target_table = args['target_table']
        s3_bucket = args['s3_bucket']
        s3_output_prefix = args['s3_output_prefix']

        # Initialize AWS clients
        s3_client = boto3.client('s3', region_name='${region}')

        # Find the latest output data
        output_info = find_latest_output_path(s3_client, s3_bucket, s3_output_prefix)
        if not output_info:
            raise Exception("No output data found")

        latest_prefix, match_file_keys = output_info

        # Read match results
        match_records = read_match_results(s3_client, s3_bucket, match_file_keys)

        # Process match results
        processed_records = process_match_results(match_records)

        # Get Snowflake credentials
        credentials = get_snowflake_credentials(secret_name)

        # Load to Snowflake
        loaded_count = load_to_snowflake(credentials, target_table, processed_records)

        # Log the result
        logger.info(f"Job completed successfully: Loaded {loaded_count} records to Snowflake")

    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
