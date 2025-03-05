#!/bin/bash
# er_extract.sh
# This script extracts data from source systems for entity resolution processing
# It is the first phase of the entity resolution pipeline

set -e

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"entity-resolution"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
EXTRACT_TIMEOUT=3600  # Maximum execution time in seconds (1 hour)

# Log file setup
LOG_DIR="/var/log/autosys/entity-resolution"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/${TIMESTAMP}_er_extract.log"
EXECUTION_ID="${TIMESTAMP}_${RANDOM}"
METADATA_DIR="/tmp/entity-resolution/${EXECUTION_ID}"

# Create directories if they don't exist
mkdir -p "${LOG_DIR}"
mkdir -p "${METADATA_DIR}"

# Write the execution ID to a file for later stages to use
echo "${EXECUTION_ID}" > "${METADATA_DIR}/execution_id"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Main execution
log "Entity Resolution extraction phase started (Execution ID: ${EXECUTION_ID})"

# Extract data from source systems
log "Extracting data from source systems"

# Example extraction commands - replace with actual extraction logic
log "Extracting customer data from S3"
aws s3 cp "s3://${PROJECT_NAME}-raw-data/customers/" "${METADATA_DIR}/customers/" --recursive --region "${AWS_REGION}"

log "Extracting transaction data from S3"
aws s3 cp "s3://${PROJECT_NAME}-raw-data/transactions/" "${METADATA_DIR}/transactions/" --recursive --region "${AWS_REGION}"

# Validate extracted data
log "Validating extracted data"
if [ ! -d "${METADATA_DIR}/customers/" ] || [ ! -d "${METADATA_DIR}/transactions/" ]; then
    log "ERROR: Required data directories not found"
    exit 1
fi

# Write extraction metadata for processing phase
cat <<EOF > "${METADATA_DIR}/extraction_metadata.json"
{
  "execution_id": "${EXECUTION_ID}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_data": {
    "customers_path": "${METADATA_DIR}/customers/",
    "transactions_path": "${METADATA_DIR}/transactions/"
  }
}
EOF

log "Extraction metadata saved to ${METADATA_DIR}/extraction_metadata.json"

# Prepare data for entity resolution
log "Preparing data for entity resolution"
aws s3 cp "${METADATA_DIR}/extraction_metadata.json" "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/extraction_metadata.json" --region "${AWS_REGION}"

log "Entity Resolution extraction phase completed successfully"
log "Execution ID: ${EXECUTION_ID}"
exit 0
