#!/bin/bash
# run_entity_resolution.sh
# This script starts an AWS Entity Resolution pipeline execution and monitors its progress
# It can be called from Autosys batch jobs

set -e

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"entity-resolution"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
STATE_MACHINE_NAME="${PROJECT_NAME}-pipeline"
EXECUTION_TIMEOUT=10800  # Maximum execution time in seconds (3 hours)
CHECK_INTERVAL=300       # How often to check status (5 minutes)

# Log file setup
LOG_DIR="/var/log/autosys/entity-resolution"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/${TIMESTAMP}_entity_resolution.log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Function to start execution
start_execution() {
    log "Starting Entity Resolution pipeline execution"
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-name "${STATE_MACHINE_NAME}" \
        --region "${AWS_REGION}" \
        --query 'executionArn' \
        --output text)

    if [ -z "${EXECUTION_ARN}" ]; then
        log "ERROR: Failed to start Step Functions execution"
        exit 1
    fi

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
log "Entity Resolution batch job started"

# Start the execution
EXECUTION_ARN=$(start_execution)

# Initialize timeout counter
ELAPSED_TIME=0

# Monitor the execution until it completes or times out
while true; do
    STATUS=$(check_execution_status "${EXECUTION_ARN}")

    if [ "${STATUS}" == "SUCCEEDED" ]; then
        log "Entity Resolution pipeline completed successfully"

        # Get execution results
        RESULT=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'output' \
            --output text)

        log "Execution result: ${RESULT}"
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

        log "ERROR: Entity Resolution pipeline failed"
        log "Error: ${ERROR}"
        log "Cause: ${CAUSE}"
        exit 1
    fi

    # Check if we've exceeded the timeout
    if [ ${ELAPSED_TIME} -ge ${EXECUTION_TIMEOUT} ]; then
        log "ERROR: Entity Resolution pipeline execution timed out after ${EXECUTION_TIMEOUT} seconds"

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
