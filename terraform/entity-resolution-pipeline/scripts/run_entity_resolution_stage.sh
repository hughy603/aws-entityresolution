#!/bin/bash
# run_entity_resolution_stage.sh
# This script handles a specific stage of the entity resolution pipeline:
# 1. extract - Extracts data from Snowflake to S3
# 2. process - Runs AWS Entity Resolution on the data
# 3. load - Loads matched results to Snowflake
#
# Usage: run_entity_resolution_stage.sh --domain DOMAIN --stage STAGE [--date DATE]

set -e

# Default values
DOMAIN=${DOMAIN:-"customers"}
PROCESS_DATE=${PROCESS_DATE:-$(date +"%Y-%m-%d")}
STAGE=${STAGE:-"process"}
CONFIG_FILE=${CONFIG_FILE:-"config.json"}
PARAMS_FILE=${PARAMS_FILE:-"/tmp/entity_resolution_params_${DOMAIN}_${PROCESS_DATE}.sh"}
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
METADATA_FILE="/tmp/entity_resolution_metadata_${DOMAIN}_${PROCESS_DATE}.json"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --stage)
            STAGE="$2"
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
LOG_FILE="${LOG_DIR}/${TIMESTAMP}_entity_resolution_${STAGE}.log"

# Helper function for logging
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "${LOG_FILE}"
}

# Add retry logic with exponential backoff
retry_with_backoff() {
    local max_attempts=$1
    local initial_wait=$2
    local max_wait=$3
    local command="${@:4}"
    local attempt=1
    local wait_time=$initial_wait
    local result

    while [ $attempt -le $max_attempts ]; do
        log "Attempt $attempt of $max_attempts: $command"
        result=$(eval "$command" 2>&1)
        exit_code=$?

        if [ $exit_code -eq 0 ]; then
            echo "$result"
            return 0
        fi

        log "Command failed with exit code $exit_code: $result"

        if [ $attempt -eq $max_attempts ]; then
            log "Maximum retry attempts reached"
            echo "$result"
            return $exit_code
        fi

        log "Waiting $wait_time seconds before retry..."
        sleep $wait_time

        # Calculate next wait time with exponential backoff
        wait_time=$(( wait_time * 2 ))
        if [ $wait_time -gt $max_wait ]; then
            wait_time=$max_wait
        fi

        attempt=$(( attempt + 1 ))
    done
}

# Generate parameter file if it doesn't exist (needed by all stages)
if [ ! -f "${PARAMS_FILE}" ]; then
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
fi

# Source the parameters file to get configuration
log "Loading parameters from ${PARAMS_FILE}"
source "${PARAMS_FILE}"

# Create a function to generate detailed job summary for email notifications
generate_job_summary() {
    local stage=$1
    local status=$2
    local stats=$3

    # Create a temporary file for the email content
    SUMMARY_FILE="/tmp/entity_resolution_${DOMAIN}_${STAGE}_${PROCESS_DATE}_summary.html"

    # Generate HTML email content with detailed information
    cat > "${SUMMARY_FILE}" << EOF
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { background-color: #${status == "SUCCESS" ? "4CAF50" : "F44336"}; color: white; padding: 10px; }
        .content { padding: 15px; }
        .stats { background-color: #f2f2f2; padding: 10px; margin: 10px 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Entity Resolution Job ${status}</h2>
    </div>
    <div class="content">
        <p><strong>Domain:</strong> ${DOMAIN}</p>
        <p><strong>Stage:</strong> ${stage}</p>
        <p><strong>Process Date:</strong> ${PROCESS_DATE}</p>
        <p><strong>Status:</strong> ${status}</p>
        <p><strong>Execution Time:</strong> $(date)</p>

        <div class="stats">
            <h3>Job Statistics</h3>
            ${stats}
        </div>

        <p>For more details, please check the log file at: ${LOG_FILE}</p>
    </div>
</body>
</html>
EOF

    log "Generated job summary for email notification"
    echo "${SUMMARY_FILE}"
}

# Function to push metrics to CloudWatch for real-time monitoring
push_cloudwatch_metrics() {
    local stage=$1
    local domain=$2
    local metric_name=$3
    local metric_value=$4
    local metric_unit=$5

    log "Publishing CloudWatch metric: ${metric_name}=${metric_value}${metric_unit} for ${domain}/${stage}"

    aws cloudwatch put-metric-data \
        --namespace "EntityResolution" \
        --metric-name "${metric_name}" \
        --dimensions "Domain=${domain},Stage=${stage},ProcessDate=${PROCESS_DATE}" \
        --value "${metric_value}" \
        --unit "${metric_unit}" \
        --region "${AWS_REGION}" > /dev/null

    if [ $? -eq 0 ]; then
        log "Successfully published metric"
    else
        log "WARNING: Failed to publish metric to CloudWatch"
    fi
}

# Function to check and alert on SLA violations
check_sla() {
    local stage=$1
    local start_time=$2
    local current_time=$(date +%s)
    local elapsed_time=$((current_time - start_time))

    # Define SLA thresholds by domain and stage (in seconds)
    case "${DOMAIN}" in
        customers)
            case "${stage}" in
                extract) SLA_THRESHOLD=1800 ;; # 30 minutes
                process) SLA_THRESHOLD=7200 ;; # 2 hours
                load) SLA_THRESHOLD=1800 ;; # 30 minutes
                *) SLA_THRESHOLD=3600 ;; # Default 1 hour
            esac
            ;;
        products)
            case "${stage}" in
                extract) SLA_THRESHOLD=3600 ;; # 1 hour
                process) SLA_THRESHOLD=14400 ;; # 4 hours
                load) SLA_THRESHOLD=3600 ;; # 1 hour
                *) SLA_THRESHOLD=7200 ;; # Default 2 hours
            esac
            ;;
        vendors)
            case "${stage}" in
                extract) SLA_THRESHOLD=2700 ;; # 45 minutes
                process) SLA_THRESHOLD=10800 ;; # 3 hours
                load) SLA_THRESHOLD=2700 ;; # 45 minutes
                *) SLA_THRESHOLD=5400 ;; # Default 1.5 hours
            esac
            ;;
        *)
            SLA_THRESHOLD=3600 ;; # Default 1 hour for unknown domains
    esac

    # Calculate SLA percentage
    SLA_PERCENTAGE=$((elapsed_time * 100 / SLA_THRESHOLD))

    # Push metric for SLA tracking
    push_cloudwatch_metrics "${stage}" "${DOMAIN}" "SLAPercentage" "${SLA_PERCENTAGE}" "Percent"

    # Check if we're approaching SLA threshold
    if [ ${SLA_PERCENTAGE} -ge 80 ] && [ ${SLA_PERCENTAGE} -lt 100 ]; then
        log "WARNING: Approaching SLA threshold (${SLA_PERCENTAGE}% of allotted time used)"

        # Send warning notification about approaching SLA
        SLA_WARNING="Domain: ${DOMAIN}, Stage: ${stage}, Process Date: ${PROCESS_DATE} is approaching SLA threshold (${SLA_PERCENTAGE}% of allotted time used)"
        aws sns publish \
            --topic-arn "${SNS_ALERT_TOPIC}" \
            --subject "SLA Warning: Entity Resolution ${DOMAIN}/${stage}" \
            --message "${SLA_WARNING}" \
            --region "${AWS_REGION}" > /dev/null

    elif [ ${SLA_PERCENTAGE} -ge 100 ]; then
        log "CRITICAL: SLA threshold exceeded (${SLA_PERCENTAGE}% of allotted time used)"

        # Send critical alert for SLA violation
        SLA_ALERT="SLA VIOLATION: Domain: ${DOMAIN}, Stage: ${stage}, Process Date: ${PROCESS_DATE} has exceeded SLA threshold (${SLA_PERCENTAGE}% of allotted time used)"
        aws sns publish \
            --topic-arn "${SNS_ALERT_TOPIC}" \
            --subject "SLA VIOLATION: Entity Resolution ${DOMAIN}/${stage}" \
            --message "${SLA_ALERT}" \
            --region "${AWS_REGION}" > /dev/null
    fi
}

# Function to extract data from Snowflake to S3
extract_data() {
    log "Starting data extraction from Snowflake to S3 for domain: ${DOMAIN}"

    # Create SQL file for the extraction
    EXTRACT_SQL="/tmp/extract_${DOMAIN}_${PROCESS_DATE}.sql"
    cat > "${EXTRACT_SQL}" << EOF
-- Extract data from ${SOURCE_TABLE} for entity resolution
COPY INTO @${S3_BUCKET_NAME}/${S3_INPUT_PREFIX}/${PROCESS_DATE}/data.csv
FROM (
    SELECT *
    FROM ${SOURCE_TABLE}
    WHERE processing_date = '${PROCESS_DATE}'
)
FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = ',' SKIP_HEADER = 1)
HEADER = TRUE
OVERWRITE = TRUE;
EOF

    # Run Snowflake extraction
    log "Executing Snowflake extraction"
    EXTRACTION_START_TIME=$(date +%s)
    snowsql -c entity_resolution -f "${EXTRACT_SQL}" -o output_format=csv -o friendly=false

    if [ $? -ne 0 ]; then
        log "ERROR: Snowflake extraction failed"

        # Generate failure summary for email notification
        STATS="<p>Extraction failed at $(date)</p>"
        generate_job_summary "extract" "FAILED" "${STATS}"

        exit 1
    fi

    EXTRACTION_END_TIME=$(date +%s)
    EXTRACTION_DURATION=$((EXTRACTION_END_TIME - EXTRACTION_START_TIME))

    # Get the S3 path for the extracted data
    S3_PATH="s3://${S3_BUCKET_NAME}/${S3_INPUT_PREFIX}/${PROCESS_DATE}/data.csv"
    log "Data extracted successfully to: ${S3_PATH}"

    # Get record count from extracted file (if possible)
    RECORD_COUNT=$(aws s3 cp "${S3_PATH}" - | wc -l)
    if [ $? -eq 0 ]; then
        # Subtract 1 for header row if it exists
        RECORD_COUNT=$((RECORD_COUNT - 1))
        log "Extracted ${RECORD_COUNT} records"
    else
        RECORD_COUNT="unknown"
    fi

    # Calculate dynamic timeout based on data volume for next stages
    if [ "${RECORD_COUNT}" != "unknown" ]; then
        # Publish metrics for record count and duration
        push_cloudwatch_metrics "extract" "${DOMAIN}" "RecordCount" "${RECORD_COUNT}" "Count"
        push_cloudwatch_metrics "extract" "${DOMAIN}" "Duration" "${EXTRACTION_DURATION}" "Seconds"

        # Base processing time calculation:
        # - 5 mins base time + 1 second per 10 records (adjust based on performance data)
        ESTIMATED_PROCESS_TIME=$((300 + RECORD_COUNT / 10))

        # Set a minimum and maximum timeout
        if [ ${ESTIMATED_PROCESS_TIME} -lt 1800 ]; then
            ESTIMATED_PROCESS_TIME=1800  # Minimum 30 mins
        elif [ ${ESTIMATED_PROCESS_TIME} -gt 43200 ]; then
            ESTIMATED_PROCESS_TIME=43200  # Maximum 12 hours
        fi

        log "Setting dynamic timeout of ${ESTIMATED_PROCESS_TIME} seconds based on ${RECORD_COUNT} records"

        # Store the dynamic timeout in metadata for subsequent stages
        cat > "${METADATA_FILE}" << EOF
{
    "domain": "${DOMAIN}",
    "process_date": "${PROCESS_DATE}",
    "source_table": "${SOURCE_TABLE}",
    "target_table": "${TARGET_TABLE}",
    "s3_input_path": "${S3_PATH}",
    "record_count": "${RECORD_COUNT}",
    "extraction_duration_seconds": ${EXTRACTION_DURATION},
    "extract_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "estimated_process_time": ${ESTIMATED_PROCESS_TIME}
}
EOF
    else
        # Default metadata without dynamic timeout
        cat > "${METADATA_FILE}" << EOF
{
    "domain": "${DOMAIN}",
    "process_date": "${PROCESS_DATE}",
    "source_table": "${SOURCE_TABLE}",
    "target_table": "${TARGET_TABLE}",
    "s3_input_path": "${S3_PATH}",
    "record_count": "${RECORD_COUNT}",
    "extraction_duration_seconds": ${EXTRACTION_DURATION},
    "extract_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    fi

    # Generate success summary for potential email notification
    STATS="<table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Source Table</td><td>${SOURCE_TABLE}</td></tr>
        <tr><td>Extracted Records</td><td>${RECORD_COUNT}</td></tr>
        <tr><td>Extraction Duration</td><td>${EXTRACTION_DURATION} seconds</td></tr>
        <tr><td>Output Location</td><td>${S3_PATH}</td></tr>
    </table>"

    generate_job_summary "extract" "SUCCESS" "${STATS}"

    log "Extraction completed successfully"
    return 0
}

# Function to process data through AWS Entity Resolution
process_data() {
    log "Starting Entity Resolution processing for domain: ${DOMAIN}"

    # Check if metadata file exists from extract step
    if [ ! -f "${METADATA_FILE}" ]; then
        log "WARNING: Metadata file not found, creating a new one"
        # Create minimal metadata if extraction was run separately
        cat > "${METADATA_FILE}" << EOF
{
    "domain": "${DOMAIN}",
    "process_date": "${PROCESS_DATE}",
    "source_table": "${SOURCE_TABLE}",
    "target_table": "${TARGET_TABLE}",
    "s3_input_path": "s3://${S3_BUCKET_NAME}/${S3_INPUT_PREFIX}/${PROCESS_DATE}/data.csv",
    "extract_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    fi

    # Load metadata
    METADATA=$(cat "${METADATA_FILE}")
    S3_INPUT_PATH=$(echo "${METADATA}" | jq -r '.s3_input_path')

    log "Using input data from: ${S3_INPUT_PATH}"

    # Create input payload for Step Functions
    OUTPUT_PREFIX="${S3_OUTPUT_PREFIX}/${PROCESS_DATE}"
    PAYLOAD=$(cat <<EOF
{
    "domain": "${DOMAIN}",
    "processDate": "${PROCESS_DATE}",
    "sourceTable": "${SOURCE_TABLE}",
    "targetTable": "${TARGET_TABLE}",
    "s3Bucket": "${S3_BUCKET_NAME}",
    "s3InputPath": "${S3_INPUT_PATH}",
    "s3OutputPrefix": "${OUTPUT_PREFIX}"
}
EOF
)

    log "Starting Step Functions execution for entity resolution"
    # Start the Step Functions execution with the payload
    EXECUTION_ARN=$(retry_with_backoff 3 5 60 "aws stepfunctions start-execution \
        --state-machine-name \"${PROJECT_NAME}-pipeline\" \
        --input \"${PAYLOAD}\" \
        --region \"${AWS_REGION}\" \
        --query 'executionArn' \
        --output text")

    if [ -z "${EXECUTION_ARN}" ]; then
        log "ERROR: Failed to start Step Functions execution"
        exit 1
    fi

    log "Started execution with ARN: ${EXECUTION_ARN}"

    # Monitor the execution until it completes or times out
    ELAPSED_TIME=0

    # Use dynamic timeout from metadata if available
    if [ -f "${METADATA_FILE}" ]; then
        DYNAMIC_TIMEOUT=$(jq -r '.estimated_process_time // "0"' "${METADATA_FILE}")
        if [ "${DYNAMIC_TIMEOUT}" != "0" ] && [ "${DYNAMIC_TIMEOUT}" != "null" ]; then
            log "Using dynamically calculated timeout of ${DYNAMIC_TIMEOUT} seconds based on data volume"
            EXECUTION_TIMEOUT=${DYNAMIC_TIMEOUT}
        else
            EXECUTION_TIMEOUT=${EXECUTION_TIMEOUT:-10800}  # Default 3 hours if not calculated
            log "Using default timeout of ${EXECUTION_TIMEOUT} seconds"
        fi
    else
        EXECUTION_TIMEOUT=${EXECUTION_TIMEOUT:-10800}  # Default 3 hours
        log "Using default timeout of ${EXECUTION_TIMEOUT} seconds"
    fi

    CHECK_INTERVAL=${CHECK_INTERVAL:-300}          # 5 minutes default
    PROCESS_START_TIME=$(date +%s)

    while true; do
        log "Checking execution status for: ${EXECUTION_ARN}"
        STATUS=$(aws stepfunctions describe-execution \
            --execution-arn "${EXECUTION_ARN}" \
            --region "${AWS_REGION}" \
            --query 'status' \
            --output text)

        log "Current status: ${STATUS}"

        if [ "${STATUS}" == "SUCCEEDED" ]; then
            log "Entity Resolution processing completed successfully"

            PROCESS_END_TIME=$(date +%s)
            PROCESS_DURATION=$((PROCESS_END_TIME - PROCESS_START_TIME))

            # Get execution results
            RESULT=$(aws stepfunctions describe-execution \
                --execution-arn "${EXECUTION_ARN}" \
                --region "${AWS_REGION}" \
                --query 'output' \
                --output text)

            log "Execution result: ${RESULT}"

            # Process the result and save metadata for next step
            OUTPUT_LOCATION=$(echo "${RESULT}" | jq -r '.body.output_location // ""')
            MATCHED_RECORDS=$(echo "${RESULT}" | jq -r '.body.matched_records // "unknown"')
            INPUT_RECORDS=$(echo "${RESULT}" | jq -r '.body.input_records // "unknown"')

            if [ -n "${OUTPUT_LOCATION}" ]; then
                # Update metadata for load step
                cat > "${METADATA_FILE}" << EOF
{
    "domain": "${DOMAIN}",
    "process_date": "${PROCESS_DATE}",
    "source_table": "${SOURCE_TABLE}",
    "target_table": "${TARGET_TABLE}",
    "s3_input_path": "${S3_INPUT_PATH}",
    "s3_output_path": "${OUTPUT_LOCATION}",
    "matched_records": ${MATCHED_RECORDS},
    "input_records": ${INPUT_RECORDS},
    "process_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
            else
                log "WARNING: No output location found in result"
            fi

            # Log matching stats if available
            if [[ "${MATCHED_RECORDS}" != "unknown" && "${INPUT_RECORDS}" != "unknown" ]]; then
                if [[ "${INPUT_RECORDS}" != "0" ]]; then
                    MATCH_RATE=$(echo "scale=2; ${MATCHED_RECORDS} * 100 / ${INPUT_RECORDS}" | bc)
                    log "Match rate: ${MATCH_RATE}%"

                    # Publish metrics
                    push_cloudwatch_metrics "process" "${DOMAIN}" "InputRecords" "${INPUT_RECORDS}" "Count"
                    push_cloudwatch_metrics "process" "${DOMAIN}" "MatchedRecords" "${MATCHED_RECORDS}" "Count"
                    push_cloudwatch_metrics "process" "${DOMAIN}" "MatchRate" "${MATCH_RATE}" "Percent"
                    push_cloudwatch_metrics "process" "${DOMAIN}" "Duration" "${PROCESS_DURATION}" "Seconds"
                fi
                log "Processed ${INPUT_RECORDS} input records with ${MATCHED_RECORDS} matches"
            fi

            # Create detailed stats for email notification
            STATS="<table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Input Records</td><td>${INPUT_RECORDS}</td></tr>
                <tr><td>Matched Records</td><td>${MATCHED_RECORDS}</td></tr>
                <tr><td>Match Rate</td><td>${MATCH_RATE}%</td></tr>
                <tr><td>Processing Duration</td><td>${PROCESS_DURATION} seconds</td></tr>
                <tr><td>Output Location</td><td>${OUTPUT_LOCATION}</td></tr>
                <tr><td>Step Functions Execution</td><td>${EXECUTION_ARN}</td></tr>
            </table>"

            generate_job_summary "process" "SUCCESS" "${STATS}"

            break
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

            PROCESS_END_TIME=$(date +%s)
            PROCESS_DURATION=$((PROCESS_END_TIME - PROCESS_START_TIME))

            # Create detailed stats for email notification
            STATS="<table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Failure Reason</td><td>${ERROR}</td></tr>
                <tr><td>Failure Details</td><td>${CAUSE}</td></tr>
                <tr><td>Duration Until Failure</td><td>${PROCESS_DURATION} seconds</td></tr>
                <tr><td>Input Path</td><td>${S3_INPUT_PATH}</td></tr>
                <tr><td>Step Functions Execution</td><td>${EXECUTION_ARN}</td></tr>
            </table>"

            generate_job_summary "process" "FAILED" "${STATS}"

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

    log "Processing completed successfully"
    return 0
}

# Function to load data from S3 to Snowflake
load_data() {
    log "Starting data load to Snowflake for domain: ${DOMAIN}"

    # Check if metadata file exists from process step
    if [ ! -f "${METADATA_FILE}" ]; then
        log "ERROR: Metadata file not found, cannot proceed with loading"
        exit 1
    fi

    # Load metadata
    METADATA=$(cat "${METADATA_FILE}")
    S3_OUTPUT_PATH=$(echo "${METADATA}" | jq -r '.s3_output_path // ""')

    if [ -z "${S3_OUTPUT_PATH}" ]; then
        log "ERROR: No output path found in metadata"
        exit 1
    fi

    log "Loading matched data from: ${S3_OUTPUT_PATH}"

    # Create SQL file for the load operation
    LOAD_SQL="/tmp/load_${DOMAIN}_${PROCESS_DATE}.sql"
    cat > "${LOAD_SQL}" << EOF
-- Load matched data to ${TARGET_TABLE}
CREATE OR REPLACE TEMPORARY TABLE ${TARGET_TABLE}_TEMP (
    -- Schema is domain-specific, so we'll use a VARIANT column to load all data
    data VARIANT
);

-- Copy from S3 to temp table
COPY INTO ${TARGET_TABLE}_TEMP (data)
FROM '${S3_OUTPUT_PATH}'
FILE_FORMAT = (TYPE = 'JSON');

-- Insert from temp table to target table with appropriate transformations
INSERT INTO ${TARGET_TABLE} (
    -- We'll insert a few key columns explicitly for tracking
    SOURCE_ID,
    MATCHED_ID,
    MATCH_CONFIDENCE_SCORE,
    PROCESS_DATE,
    MATCHING_WORKFLOW,
    LOAD_TIMESTAMP
    -- Other columns would be inserted based on domain-specific schema
)
SELECT
    data:sourceId::STRING AS SOURCE_ID,
    data:matchedId::STRING AS MATCHED_ID,
    data:confidenceScore::FLOAT AS MATCH_CONFIDENCE_SCORE,
    '${PROCESS_DATE}' AS PROCESS_DATE,
    '${ER_WORKFLOW_NAME}' AS MATCHING_WORKFLOW,
    CURRENT_TIMESTAMP() AS LOAD_TIMESTAMP
FROM ${TARGET_TABLE}_TEMP;

-- Get count of loaded records
SELECT COUNT(*) AS LOADED_RECORDS FROM ${TARGET_TABLE}
WHERE PROCESS_DATE = '${PROCESS_DATE}'
AND MATCHING_WORKFLOW = '${ER_WORKFLOW_NAME}';
EOF

    # Run Snowflake load
    log "Executing Snowflake load"
    LOAD_START_TIME=$(date +%s)
    LOAD_RESULT=$(snowsql -c entity_resolution -f "${LOAD_SQL}" -o output_format=csv -o friendly=false)

    if [ $? -ne 0 ]; then
        log "ERROR: Snowflake load failed"
        log "Error details: ${LOAD_RESULT}"

        # Generate failure summary for email notification
        STATS="<table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Failure Reason</td><td>Snowflake load operation failed</td></tr>
            <tr><td>Source S3 Path</td><td>${S3_OUTPUT_PATH}</td></tr>
            <tr><td>Target Table</td><td>${TARGET_TABLE}</td></tr>
        </table>
        <p>Error details:</p>
        <pre>${LOAD_RESULT}</pre>"

        generate_job_summary "load" "FAILED" "${STATS}"

        exit 1
    fi

    LOAD_END_TIME=$(date +%s)
    LOAD_DURATION=$((LOAD_END_TIME - LOAD_START_TIME))

    # Extract loaded record count from result
    LOADED_RECORDS=$(echo "${LOAD_RESULT}" | grep -o '[0-9]\+' | tail -1)

    # Update metadata with load information
    cat > "${METADATA_FILE}" << EOF
{
    "domain": "${DOMAIN}",
    "process_date": "${PROCESS_DATE}",
    "source_table": "${SOURCE_TABLE}",
    "target_table": "${TARGET_TABLE}",
    "s3_input_path": "$(echo "${METADATA}" | jq -r '.s3_input_path')",
    "s3_output_path": "${S3_OUTPUT_PATH}",
    "matched_records": $(echo "${METADATA}" | jq -r '.matched_records // "unknown"'),
    "input_records": $(echo "${METADATA}" | jq -r '.input_records // "unknown"'),
    "loaded_records": ${LOADED_RECORDS},
    "load_duration_seconds": ${LOAD_DURATION},
    "process_timestamp": "$(echo "${METADATA}" | jq -r '.process_timestamp // ""')",
    "load_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

    log "Successfully loaded ${LOADED_RECORDS} records to ${TARGET_TABLE}"

    # Publish metrics for load stage
    push_cloudwatch_metrics "load" "${DOMAIN}" "LoadedRecords" "${LOADED_RECORDS}" "Count"
    push_cloudwatch_metrics "load" "${DOMAIN}" "Duration" "${LOAD_DURATION}" "Seconds"

    # Generate comprehensive summary for success email notification
    INPUT_RECORDS=$(echo "${METADATA}" | jq -r '.input_records // "unknown"')
    MATCHED_RECORDS=$(echo "${METADATA}" | jq -r '.matched_records // "unknown"')

    # Calculate match rate if possible
    if [[ "${MATCHED_RECORDS}" != "unknown" && "${INPUT_RECORDS}" != "unknown" && "${INPUT_RECORDS}" != "0" ]]; then
        MATCH_RATE=$(echo "scale=2; ${MATCHED_RECORDS} * 100 / ${INPUT_RECORDS}" | bc)
    else
        MATCH_RATE="unknown"
    fi

    # Create detailed stats for email notification with complete pipeline summary
    STATS="<table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Domain</td><td>${DOMAIN}</td></tr>
        <tr><td>Process Date</td><td>${PROCESS_DATE}</td></tr>
        <tr><td>Source Table</td><td>${SOURCE_TABLE}</td></tr>
        <tr><td>Target Table</td><td>${TARGET_TABLE}</td></tr>
        <tr><td>Input Records</td><td>${INPUT_RECORDS}</td></tr>
        <tr><td>Matched Records</td><td>${MATCHED_RECORDS}</td></tr>
        <tr><td>Match Rate</td><td>${MATCH_RATE}%</td></tr>
        <tr><td>Loaded Records</td><td>${LOADED_RECORDS}</td></tr>
        <tr><td>Load Duration</td><td>${LOAD_DURATION} seconds</td></tr>
    </table>

    <h3>Pipeline Summary</h3>
    <p>The entity resolution pipeline for ${DOMAIN} domain completed successfully. The process extracted ${INPUT_RECORDS} records,
    found ${MATCHED_RECORDS} matches (${MATCH_RATE}% match rate), and loaded ${LOADED_RECORDS} records to the target table.</p>"

    SUMMARY_FILE=$(generate_job_summary "load" "SUCCESS" "${STATS}")

    # Save the summary to S3 for reference
    SUMMARY_S3_PATH="s3://${S3_BUCKET_NAME}/${S3_OUTPUT_PREFIX}/summaries/${PROCESS_DATE}_${DOMAIN}_summary.html"
    aws s3 cp "${SUMMARY_FILE}" "${SUMMARY_S3_PATH}"

    if [ $? -eq 0 ]; then
        log "Job summary saved to ${SUMMARY_S3_PATH}"
    fi

    log "Load operation completed successfully"
    return 0
}

# Main execution flow
log "Entity Resolution [${STAGE}] job started for domain: ${DOMAIN}, date: ${PROCESS_DATE}"

case "${STAGE}" in
    extract)
        extract_data
        ;;
    process)
        process_data
        ;;
    load)
        load_data
        ;;
    *)
        log "ERROR: Unknown stage '${STAGE}'. Valid stages are: extract, process, load"
        exit 1
        ;;
esac

# If we got here, the stage completed successfully
log "Entity Resolution ${STAGE} stage completed successfully for domain: ${DOMAIN}"
exit 0
