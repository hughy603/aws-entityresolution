#!/bin/bash
# run_entity_resolution_domain.sh
# This script runs entity resolution for a specific domain using the AWS Step Functions workflow
# It can be called from Autosys batch jobs with specific parameters

set -e

# Default values
DOMAIN=${DOMAIN:-"customers"}
PROCESS_DATE=${PROCESS_DATE:-$(date +"%Y-%m-%d")}
CONFIG_FILE=${CONFIG_FILE:-"config.json"}
PARAMS_FILE=${PARAMS_FILE:-"/tmp/entity_resolution_params_${DOMAIN}_${PROCESS_DATE}.sh"}
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --date)
            PROCESS_DATE="$2"
            shift 2
            ;;
        --input-table)
            INPUT_TABLE="$2"
            shift 2
            ;;
        --output-table)
            OUTPUT_TABLE="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --params-file)
            PARAMS_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set up log file
LOG_DIR="/var/log/autosys/entity-resolution/${DOMAIN}"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/${TIMESTAMP}_entity_resolution.log"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Generate parameter file
log "Generating parameters for domain: ${DOMAIN}, date: ${PROCESS_DATE}"
PARAM_CMD="${SCRIPT_DIR}/generate_entity_resolution_params.py --domain ${DOMAIN} --date ${PROCESS_DATE} --config-file ${CONFIG_FILE} --output-file ${PARAMS_FILE}"

if [ -n "${INPUT_TABLE}" ]; then
    PARAM_CMD="${PARAM_CMD} --input-table ${INPUT_TABLE}"
fi

if [ -n "${OUTPUT_TABLE}" ]; then
    PARAM_CMD="${PARAM_CMD} --output-table ${OUTPUT_TABLE}"
fi

log "Running: ${PARAM_CMD}"
python3 ${PARAM_CMD}

if [ $? -ne 0 ]; then
    log "ERROR: Failed to generate parameters"
    exit 1
fi

# Source the parameters file
log "Loading parameters from ${PARAMS_FILE}"
source "${PARAMS_FILE}"

# Function to start execution
start_execution() {
    log "Starting Entity Resolution pipeline execution for domain: ${DOMAIN}"

    # Create input payload with domain-specific parameters
    PAYLOAD=$(cat <<EOF
{
    "domain": "${DOMAIN}",
    "processDate": "${PROCESS_DATE}",
    "sourceTable": "${SOURCE_TABLE}",
    "targetTable": "${TARGET_TABLE}",
    "s3Bucket": "${S3_BUCKET_NAME}",
    "s3InputPrefix": "${S3_INPUT_PREFIX}",
    "s3OutputPrefix": "${S3_OUTPUT_PREFIX}"
}
EOF
)

    # Start the Step Functions execution with the payload
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-name "${PROJECT_NAME}-pipeline" \
        --input "${PAYLOAD}" \
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
log "Entity Resolution batch job started for domain: ${DOMAIN}"

# Start the execution
EXECUTION_ARN=$(start_execution)

# Initialize timeout counter
ELAPSED_TIME=0
# Maximum execution time in seconds (3 hours by default)
EXECUTION_TIMEOUT=${EXECUTION_TIMEOUT:-10800}
# How often to check status (5 minutes by default)
CHECK_INTERVAL=${CHECK_INTERVAL:-300}

# Monitor the execution until it completes or times out
while true; do
    STATUS=$(check_execution_status "${EXECUTION_ARN}")

    if [ "${STATUS}" == "SUCCEEDED" ]; then
        log "Entity Resolution pipeline completed successfully for domain: ${DOMAIN}"

        # Get execution results
        RESULT=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'output' \
            --output text)

        log "Execution result: ${RESULT}"

        # Report completion statistics if available
        if echo "${RESULT}" | grep -q "matched_records"; then
            MATCHED_RECORDS=$(echo "${RESULT}" | jq -r '.body.matched_records // "unknown"')
            INPUT_RECORDS=$(echo "${RESULT}" | jq -r '.body.input_records // "unknown"')

            log "Processed ${INPUT_RECORDS} input records with ${MATCHED_RECORDS} matches"

            # Calculate match rate if available
            if [[ "${MATCHED_RECORDS}" != "unknown" && "${INPUT_RECORDS}" != "unknown" && "${INPUT_RECORDS}" != "0" ]]; then
                MATCH_RATE=$(echo "scale=2; ${MATCHED_RECORDS} * 100 / ${INPUT_RECORDS}" | bc)
                log "Match rate: ${MATCH_RATE}%"
            fi
        fi

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

        log "ERROR: Entity Resolution pipeline failed for domain: ${DOMAIN}"
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
