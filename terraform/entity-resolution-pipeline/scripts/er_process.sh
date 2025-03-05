#!/bin/bash
# er_process.sh
# This script starts an AWS Entity Resolution pipeline execution and monitors its progress
# It is the second phase of the entity resolution pipeline

set -e

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"entity-resolution"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
STATE_MACHINE_NAME="${PROJECT_NAME}-pipeline"
EXECUTION_TIMEOUT=10800  # Maximum execution time in seconds (3 hours)
CHECK_INTERVAL=300       # How often to check status (5 minutes)

# Get the execution ID from the extraction phase
if [ -f "/tmp/entity-resolution/*/execution_id" ]; then
    EXECUTION_ID=$(cat $(ls -t /tmp/entity-resolution/*/execution_id | head -1))
else
    echo "ERROR: No execution ID found from extraction phase"
    exit 1
fi

# Log file setup
LOG_DIR="/var/log/autosys/entity-resolution"
LOG_FILE="${LOG_DIR}/${EXECUTION_ID}_er_process.log"
METADATA_DIR="/tmp/entity-resolution/${EXECUTION_ID}"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Function to start execution
start_execution() {
    log "Starting Entity Resolution pipeline execution"

    # Read extraction metadata
    if [ ! -f "${METADATA_DIR}/extraction_metadata.json" ]; then
        # Try to download it from S3 if not found locally
        aws s3 cp "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/extraction_metadata.json" "${METADATA_DIR}/extraction_metadata.json" --region "${AWS_REGION}"

        if [ ! -f "${METADATA_DIR}/extraction_metadata.json" ]; then
            log "ERROR: Extraction metadata not found"
            exit 1
        fi
    fi

    # Prepare input for step function
    cat <<EOF > "${METADATA_DIR}/step_function_input.json"
{
  "executionId": "${EXECUTION_ID}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "extractionMetadataPath": "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/extraction_metadata.json"
}
EOF

    # Start step function execution
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-name "${STATE_MACHINE_NAME}" \
        --input file://${METADATA_DIR}/step_function_input.json \
        --region "${AWS_REGION}" \
        --query 'executionArn' \
        --output text)

    if [ -z "${EXECUTION_ARN}" ]; then
        log "ERROR: Failed to start Step Functions execution"
        exit 1
    fi

    # Save execution ARN for reference
    echo "${EXECUTION_ARN}" > "${METADATA_DIR}/step_function_arn"

    log "Started execution with ARN: ${EXECUTION_ARN}"
    echo "${EXECUTION_ARN}"
}

# Function to check execution status
check_execution_status() {
    local execution_arn="$1"

    log "Checking execution status for: ${execution_arn}"
    STATUS=$(aws stepfunctions describe-execution \
        --execution-arn "${execution_arn}" \
        --region "${AWS_REGION}" \
        --query 'status' \
        --output text)

    log "Current status: ${STATUS}"
    echo "${STATUS}"
}

# Main execution
log "Entity Resolution processing phase started (Execution ID: ${EXECUTION_ID})"

# Start the execution
EXECUTION_ARN=$(start_execution)

# Initialize timeout counter
ELAPSED_TIME=0

# Monitor the execution until it completes or times out
while true; do
    STATUS=$(check_execution_status "${EXECUTION_ARN}")

    if [ "${STATUS}" == "SUCCEEDED" ]; then
        log "Entity Resolution processing completed successfully"

        # Get execution results
        RESULT=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'output' \
            --output text)

        # Save results for the load phase
        echo "${RESULT}" > "${METADATA_DIR}/processing_results.json"

        # Copy results to S3
        aws s3 cp "${METADATA_DIR}/processing_results.json" "s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/processing_results.json" --region "${AWS_REGION}"

        log "Processing results saved to: s3://${PROJECT_NAME}-staging/executions/${EXECUTION_ID}/processing_results.json"
        exit 0
    elif [ "${STATUS}" == "FAILED" ] || [ "${STATUS}" == "ABORTED" ] || [ "${STATUS}" == "TIMED_OUT" ]; then
        ERROR=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'error' \
            --output text)

        CAUSE=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'cause' \
            --output text)

        log "ERROR: Entity Resolution processing failed"
        log "Error: ${ERROR}"
        log "Cause: ${CAUSE}"
        exit 1
    fi

    # Check if we've exceeded the timeout
    if [ ${ELAPSED_TIME} -ge ${EXECUTION_TIMEOUT} ]; then
        log "ERROR: Entity Resolution processing timed out after ${EXECUTION_TIMEOUT} seconds"

        # Try to stop the execution
        aws stepfunctions stop-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --cause "Stopped by Autosys job due to timeout"

        exit 1
    fi

    # Wait before checking again
    log "Waiting ${CHECK_INTERVAL} seconds before checking again..."
    sleep ${CHECK_INTERVAL}

    # Update elapsed time
    ELAPSED_TIME=$((ELAPSED_TIME + CHECK_INTERVAL))
done
