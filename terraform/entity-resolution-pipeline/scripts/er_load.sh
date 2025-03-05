#!/bin/bash
# er_load.sh
# This script loads entity resolution results to Snowflake
# It is the third phase of the entity resolution pipeline

set -e

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"entity-resolution"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT:-"myaccount"}
SNOWFLAKE_USER=${SNOWFLAKE_USER:-"er_service"}
SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE:-"entity_resolution_wh"}
SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE:-"entity_resolution"}
SNOWFLAKE_SCHEMA=${SNOWFLAKE_SCHEMA:-"public"}
SNOWFLAKE_ROLE=${SNOWFLAKE_ROLE:-"entity_resolution_role"}
SNOWFLAKE_PASSWORD_SECRET="${PROJECT_NAME}-snowflake-password"
LOAD_TIMEOUT=3600  # Maximum execution time in seconds (1 hour)

# Get the execution ID from the extraction phase
if [ -f "/tmp/entity-resolution/*/execution_id" ]; then
    EXECUTION_ID=$(cat $(ls -t /tmp/entity-resolution/*/execution_id | head -1))
else
    echo "ERROR: No execution ID found from extraction phase"
    exit 1
fi

# Log file setup
LOG_DIR="/var/log/autosys/entity-resolution"
LOG_FILE="${LOG_DIR}/${EXECUTION_ID}_er_load.log"
METADATA_DIR="/tmp/entity-resolution/${EXECUTION_ID}"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Function to retrieve Snowflake password from AWS Secrets Manager
get_snowflake_password() {
    SNOWFLAKE_PASSWORD=$(aws secretsmanager get-secret-value \
        --secret-id "${SNOWFLAKE_PASSWORD_SECRET}" \
        --region "${AWS_REGION}" \
        --query 'SecretString' \
        --output text)

    if [ -z "${SNOWFLAKE_PASSWORD}" ]; then
        log "ERROR: Failed to retrieve Snowflake password from Secrets Manager"
        exit 1
    fi
}

# Function to prepare data for loading to Snowflake
prepare_data() {
    log "Preparing data for Snowflake load"

    # Check if processing results exist locally
    if [ ! -f "${METADATA_DIR}/processing_results.json" ]; then
        # Try to download from S3
        aws s3 cp "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/processing_results.json" "${METADATA_DIR}/processing_results.json" --region "${AWS_REGION}"

        if [ ! -f "${METADATA_DIR}/processing_results.json" ]; then
            log "ERROR: Processing results not found"
            exit 1
        fi
    fi

    # Extract and transform the results for Snowflake
    log "Transforming entity resolution results for Snowflake format"

    # Create a staging directory for CSV files
    mkdir -p "${METADATA_DIR}/snowflake_stage"

    # Convert JSON results to CSV format (simplified example)
    # In a real implementation, you would use proper JSON parsing (e.g., with jq)
    python3 -c "
import json
import csv
import os

# Load the processing results
with open('${METADATA_DIR}/processing_results.json', 'r') as f:
    data = json.load(f)

# Extract match results
matches = data.get('matches', [])
if not matches:
    print('No matches found in the results')
    exit(1)

# Write matches to CSV
with open('${METADATA_DIR}/snowflake_stage/matches.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['execution_id', 'match_id', 'confidence_score', 'source_id', 'matched_id'])

    for match in matches:
        match_id = match.get('matchId', '')
        confidence = match.get('confidenceScore', 0)
        source_id = match.get('sourceId', '')
        matched_id = match.get('matchedId', '')
        writer.writerow(['${EXECUTION_ID}', match_id, confidence, source_id, matched_id])

print(f'Processed {len(matches)} matches to CSV')
"

    # Check if the CSV file was created
    if [ ! -f "${METADATA_DIR}/snowflake_stage/matches.csv" ]; then
        log "ERROR: Failed to convert results to CSV format"
        exit 1
    fi

    log "Successfully transformed results to Snowflake format"
}

# Function to load data to Snowflake
load_to_snowflake() {
    log "Loading entity resolution results to Snowflake"

    # Get Snowflake password
    get_snowflake_password

    # Upload CSV to S3 for Snowflake external stage
    aws s3 cp "${METADATA_DIR}/snowflake_stage/" "s3://${PROJECT_NAME}-snowflake-stage/${EXECUTION_ID}/" --recursive --region "${AWS_REGION}"

    # Create Snowflake SQL for loading data
    cat <<EOF > "${METADATA_DIR}/snowflake_load.sql"
USE ROLE ${SNOWFLAKE_ROLE};
USE WAREHOUSE ${SNOWFLAKE_WAREHOUSE};
USE DATABASE ${SNOWFLAKE_DATABASE};
USE SCHEMA ${SNOWFLAKE_SCHEMA};

-- Create temporary stage
CREATE OR REPLACE TEMPORARY STAGE er_temp_stage
  URL = 's3://${PROJECT_NAME}-snowflake-stage/${EXECUTION_ID}/'
  CREDENTIALS = (AWS_ROLE = 'arn:aws:iam::ACCOUNT_ID:role/SnowflakeLoadRole');

-- Load matches data
COPY INTO entity_matches (
  execution_id,
  match_id,
  confidence_score,
  source_id,
  matched_id
)
FROM @er_temp_stage/matches.csv
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)
ON_ERROR = 'CONTINUE';

-- Record load metadata
INSERT INTO entity_resolution_loads (
  execution_id,
  load_timestamp,
  status,
  record_count
)
SELECT
  '${EXECUTION_ID}',
  CURRENT_TIMESTAMP(),
  'COMPLETED',
  COUNT(*)
FROM entity_matches
WHERE execution_id = '${EXECUTION_ID}';
EOF

    # Execute Snowflake SQL
    log "Executing Snowflake load"

    snowsql \
        -a ${SNOWFLAKE_ACCOUNT} \
        -u ${SNOWFLAKE_USER} \
        -p "${SNOWFLAKE_PASSWORD}" \
        -f "${METADATA_DIR}/snowflake_load.sql" \
        -o output_file="${METADATA_DIR}/snowflake_output.txt"

    SNOWFLAKE_EXIT_CODE=$?

    if [ ${SNOWFLAKE_EXIT_CODE} -ne 0 ]; then
        log "ERROR: Snowflake load failed with exit code ${SNOWFLAKE_EXIT_CODE}"
        if [ -f "${METADATA_DIR}/snowflake_output.txt" ]; then
            log "Snowflake error output:"
            cat "${METADATA_DIR}/snowflake_output.txt" | tee -a "${LOG_FILE}"
        fi
        exit 1
    fi

    log "Successfully loaded entity resolution results to Snowflake"
}

# Main execution
log "Entity Resolution load phase started (Execution ID: ${EXECUTION_ID})"

# Prepare data for Snowflake
prepare_data

# Load data to Snowflake
load_to_snowflake

# Record completion
log "Entity Resolution load phase completed successfully"

# Update final status in S3
echo "{\"executionId\":\"${EXECUTION_ID}\",\"status\":\"COMPLETED\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}" > "${METADATA_DIR}/pipeline_status.json"
aws s3 cp "${METADATA_DIR}/pipeline_status.json" "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/pipeline_status.json" --region "${AWS_REGION}"

exit 0
